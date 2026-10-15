"""
services/llm/tools.py — MCP tool을 provider별 스키마로 변환 + tool 사용 지시문

mcp_manager.get_tools()가 반환하는 통일 형식
  {"type":"function","function":{"name","description","parameters"}}
을 각 provider(function-calling)의 스키마로 변환한다.

- OpenAI : tools=[{type:function, function:{name,description,parameters}}]  (통일형과 동일)
- Gemini : tools=[{functionDeclarations:[{name,description,parameters}]}]
- Claude : tools=[{name,description,input_schema}]
"""


from services.prompt_processing import capture, enabled
import json

from .config import logger
from services.prompt_defaults import (
    TOOL_USAGE_TEMPLATE,
    BROWSER_TOOL_INSTRUCTION,
    CODE_COMPLETION_INSTRUCTION,
    SELECTED_TOOL_INSTRUCTION,
    UNAVAILABLE_TOOL_INSTRUCTION,
    GITHUB_CONTEXT_TEMPLATE,
    CODE_CONTEXT_TEMPLATE,
    RECIPIENT_VERIFICATION_INSTRUCTION,
)

RECIPIENT_ACTION_TOOLS = frozenset({
    "send_email", "reply_email", "create_email_draft", "create_calendar_event",
    "update_calendar_event", "microsoft_send_email", "microsoft_create_calendar_event",
})


def tool_result_failed(result_text: str) -> bool:
    if result_text.startswith(("[오류]", "[tool 오류]")):
        return True
    if not result_text.lstrip().startswith("{"):
        return False
    try:
        payload = json.loads(result_text)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and (payload.get("ok") is False or bool(payload.get("error")))


def build_approval_rejection_instruction(tool_name: str) -> str:
    """Force the final response to reflect an explicit user rejection accurately."""
    return (
        "\n\n[최우선 — 실행 미승인 결과]\n"
        f"'{tool_name}' 도구 실행에 필요한 승인을 받지 못했다. "
        "해당 도구는 실행되지 않았고 요청한 변경도 발생하지 않았다. "
        "최종 답변에서는 실행 승인을 받지 못해 작업을 수행하지 않았다고 명확히 안내해라. 승인 수단이 없어 실행되지 않은 경우를 사용자가 직접 거절한 것으로 설명하지 마라. "
        "절대로 작업이 성공했거나 처리되었다고 말하지 말고, 같은 도구를 다시 호출하지 마라."
    )


async def build_tool_directive(tool_names: list[str]) -> str:
    """작은/일반 모델이 tool을 확실히 호출하도록 유도하는 system 지시문.

    모든 provider 도구 실행 경로에서 동일한 문구를 공통으로 쓴다.
    GitHub tool이 있으면 사용자 username을 주입해 '내 저장소' 요청을 지원한다.

    일반·프로젝트 채팅은 설정의 항목 순서에 따라 조합한다.
    별도 경량·보조 호출은 기존처럼 시스템 본문 뒤에 붙인다.
    실제 노출된 MCP 서버의 사용자 지정 프롬프트만 함께 주입한다.

    작업 설명은 별도 LLM 호출로 생성하지 않고 첫 streaming 응답의
    tool_calls 직전 content로 받는다. 그래야 tool 결과를 뒤에 append하는
    기존 메시지 prefix와 local runtime prefix cache 흐름을 유지할 수 있다.
    """
    directive = TOOL_USAGE_TEMPLATE.format(tool_names=', '.join(tool_names))
    directive = capture("tools", directive)
    # @로 특정 MCP를 고른 것은 사용자가 해당 MCP를 이번 요청의 실행 수단으로
    # 명시한 것이므로, 모델이 자체 지식으로 바로 답하지 못하게 강하게 유도한다.
    selected_server_ids = None
    try:
        from services.mcp_client import mcp_manager
        selected_server_ids = mcp_manager.get_request_scope_server_ids()
        if mcp_manager.has_request_scope():
            exposed_ids, exposed_types = mcp_manager.exposed_server_scopes(tool_names)
            selected_types = mcp_manager.get_request_scope_server_types() or set()
            if (selected_server_ids or set()) & exposed_ids or selected_types & exposed_types:
                directive += SELECTED_TOOL_INSTRUCTION
            else:
                directive += UNAVAILABLE_TOOL_INSTRUCTION
    except Exception as _scope_error:
        logger.debug("[tools] 선택 MCP 지시 확인 실패: %s", _scope_error)
    if any(n.startswith("github_") for n in tool_names):
        try:
            from services.mcp_config import get_github_username
            gh_user = await get_github_username()
            if gh_user:
                directive += GITHUB_CONTEXT_TEMPLATE.format(github_username=gh_user)
        except Exception as _ge:
            logger.debug("[tools] github username 주입 실패: %s", _ge)

    # 코드 분석 폴더가 설정돼 있으면 코드 도구 사용 지시 추가
    if any(n.startswith("code_") for n in tool_names):
        try:
            from services.code_tools import current_code_folders
            folders = current_code_folders.get()
            if folders:
                folder_list = ", ".join(f"{folder_id} ({path})" for folder_id, path in folders.items())
                directive += CODE_CONTEXT_TEMPLATE.format(registered_folders=folder_list)
        except Exception:
            pass

    if any(n.startswith("browser_") for n in tool_names):
        directive += BROWSER_TOOL_INSTRUCTION

    try:
        from services.mcp_config import get_active_mcp_prompt
        extra = await get_active_mcp_prompt(selected_server_ids, available_tool_names=tool_names) if enabled("mcp") else ""
        if extra:
            directive += capture("mcp", f"\n\n{extra}")
    except Exception as _pe:
        logger.debug("[tools] MCP 프롬프트 재주입 실패: %s", _pe)

    if any(n.startswith("code_") for n in tool_names):
        directive += CODE_COMPLETION_INSTRUCTION

    if RECIPIENT_ACTION_TOOLS.intersection(tool_names):
        directive += RECIPIENT_VERIFICATION_INSTRUCTION

    return capture("toolContext", directive)


def to_openai_tools(unified: list[dict]) -> list[dict]:
    """통일형 → OpenAI tools (형식이 사실상 동일하지만 안전하게 재구성)."""
    out = []
    for t in unified:
        fn = t.get("function", {})
        out.append({
            "type": "function",
            "function": {
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
            },
        })
    return out


def to_gemini_tools(unified: list[dict]) -> list[dict]:
    """통일형 → Gemini tools[{functionDeclarations:[...]}].

    Gemini는 parameters의 JSON Schema에서 지원하지 않는 키가 있으면 400을 낸다.
    안전하게 type/properties/required/description/items/enum만 남긴다.
    """
    decls = []
    for t in unified:
        fn = t.get("function", {})
        decls.append({
            "name": fn.get("name"),
            "description": fn.get("description", ""),
            "parameters": _sanitize_gemini_schema(fn.get("parameters") or {"type": "object", "properties": {}}),
        })
    return [{"functionDeclarations": decls}]


def _sanitize_gemini_schema(schema: dict) -> dict:
    """Gemini functionDeclarations가 받아들이는 키만 남긴 JSON Schema로 정제."""
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}
    allowed = {"type", "description", "enum", "properties", "required", "items", "nullable"}
    out: dict = {}
    for k, v in schema.items():
        if k not in allowed:
            continue
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _sanitize_gemini_schema(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            out[k] = _sanitize_gemini_schema(v)
        else:
            out[k] = v
    if out.get("type") == "object" and "properties" not in out:
        out["properties"] = {}
    return out


def to_claude_tools(unified: list[dict]) -> list[dict]:
    """통일형 → Claude tools[{name,description,input_schema}]."""
    out = []
    for t in unified:
        fn = t.get("function", {})
        out.append({
            "name": fn.get("name"),
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out
