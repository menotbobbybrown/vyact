"""System instruction collection and compatibility assembly for auxiliary/voice requests."""
from datetime import datetime

from services.prompt_processing import capture, compose, current_composition
from .language import get_language_label
from services.prompt_defaults import (
    ADDITIONAL_INSTRUCTIONS_TEMPLATE, CONVERSATION_CONTEXT_TEMPLATE, CURRENT_DATE_TEMPLATE,
    BASE_FORMAT_INSTRUCTION, PROJECT_OUTPUT_INSTRUCTION, FOLLOWUP_INSTRUCTION,
    FORMAT_INSTRUCTION, REASONING_BUDGET_INSTRUCTION, RESPONSE_LANGUAGE_TEMPLATE,
    RESPONSE_LENGTH_INSTRUCTION, SKILL_CONTEXT_TEMPLATE, USER_PROFILE_TEMPLATE,
)


def build_system_message(
        system_prompt: str,
        format_instruction_override: str | None,
        user_profile: str = "",
        skill_context: str = "",
        conversation_summary: str = "",
        user_language: str = "",
        isolated: bool = False,
        include_response_language: bool = True,
        reasoning: bool | str = False,
) -> str:
    """Managed chats use saved composition; other callers retain their original contract."""
    language_instruction = RESPONSE_LANGUAGE_TEMPLATE.format(language=get_language_label(user_language))
    if isolated:
        return "\n\n".join(filter(None, [system_prompt, language_instruction if include_response_language else ""]))

    reasoning_enabled = reasoning is True or (
        isinstance(reasoning, str) and reasoning.lower() not in {"none", "off"}
    )
    allow_profile_and_skills = format_instruction_override != ""
    context = {
        "length": RESPONSE_LENGTH_INSTRUCTION,
        "reasoning": REASONING_BUDGET_INSTRUCTION if reasoning_enabled else "",
        "date": CURRENT_DATE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d")),
        "profile": USER_PROFILE_TEMPLATE.format(profile=user_profile) if user_profile and allow_profile_and_skills else "",
        "summary": CONVERSATION_CONTEXT_TEMPLATE.format(summary=conversation_summary) if conversation_summary else "",
        "skills": SKILL_CONTEXT_TEMPLATE.format(skills=skill_context) if skill_context and allow_profile_and_skills else "",
        "language": language_instruction if include_response_language else "",
    }
    composition = current_composition.get()
    if composition is not None:
        capture("base", format_instruction_override if format_instruction_override is not None
                else BASE_FORMAT_INSTRUCTION)
        capture("projectOutput", PROJECT_OUTPUT_INSTRUCTION)
        capture("followups", FOLLOWUP_INSTRUCTION)
        for key, text in context.items():
            capture(key, text)
        return compose()

    # Voice, lightweight clients, warm-up and auxiliary LLM callers keep legacy precedence.
    if format_instruction_override is not None:
        message = format_instruction_override
        if system_prompt:
            message = (message + ADDITIONAL_INSTRUCTIONS_TEMPLATE.format(instructions=system_prompt)
                       if message else system_prompt)
    else:
        message = system_prompt or FORMAT_INSTRUCTION
    # The empty legacy base still occupies its original position for voice-only requests.
    return "\n\n".join([message, *(text for text in context.values() if text)])
