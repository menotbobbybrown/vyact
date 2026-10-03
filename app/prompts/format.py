"""
prompts/format.py – 정적 프롬프트 상수
"""

FORMAT_INSTRUCTION = """\
## Output
Use concise Markdown, meaningful paragraphs, `###` headings, and at most two list levels. Use backticks for commands and identifiers; language-tagged code blocks with file paths for code.

For complete projects, include all key files with full contents:
<vyproject name="...">
<file path="...">complete content</file>
</vyproject>

## Follow-ups
Only for substantive informational answers, optionally append 2–3 concise next requests in the response language:
<followups>
- ...
</followups>
No visible text after these tags; required hidden metadata may follow.
"""

VOICE_MODE_SUFFIX = "\n\nDo not use emoticons or emoji."

# 크롬 확장 등 경량 클라이언트용 최소 포맷 지시.
# 확장에는 프로젝트 블록/FollowupBar/SummaryModal UI가 없으므로
# FORMAT_INSTRUCTION(코드 출력 규칙 + followups 규칙)을 통째로 빼고 이것만 쓴다.
# (QueryRequest.minimal_prompt=True 로 요청 시 적용)
EXTENSION_FORMAT_INSTRUCTION = """\
Answer concisely and accurately in Korean. Use Korean for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed."""

_EXTENSION_FORMAT_BY_LANG = {
    "ko": EXTENSION_FORMAT_INSTRUCTION,
    "en": "Answer concisely and accurately in English. Use English for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "ja": "Answer concisely and accurately in Japanese. Use Japanese for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "zh": "Answer concisely and accurately in Chinese. Use Chinese for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "th": "Answer concisely and accurately in Thai. Use Thai for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "vi": "Answer concisely and accurately in Vietnamese. Use Vietnamese for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "es": "Answer concisely and accurately in Spanish. Use Spanish for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
    "fr": "Answer concisely and accurately in French. Use French for headings and section titles. Markdown may be used. Only use code blocks with the language specified when code is needed.",
}


def get_extension_format_instruction(language: str = "en") -> str:
    return _EXTENSION_FORMAT_BY_LANG.get(language, _EXTENSION_FORMAT_BY_LANG["en"])
