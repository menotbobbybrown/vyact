"""Localized messages for the shared tool execution boundary."""
import json

from routers.deps import load_ui_language_async

_MESSAGES = {
    "en": ["Tool execution failed ({tool}): {detail}", "Invalid tool name: {tool}", "Unknown MCP server: {server}", "[Image result]", "Unknown error", "(No result)"],
    "ko": ["도구 실행 실패 ({tool}): {detail}", "잘못된 도구 이름: {tool}", "알 수 없는 MCP 서버: {server}", "[이미지 결과]", "알 수 없는 오류", "(결과 없음)"],
    "ja": ["ツールの実行に失敗しました ({tool}): {detail}", "無効なツール名: {tool}", "不明なMCPサーバー: {server}", "[画像の結果]", "不明なエラー", "(結果なし)"],
    "zh": ["工具执行失败 ({tool}): {detail}", "无效的工具名称: {tool}", "未知的MCP服务器: {server}", "[图像结果]", "未知错误", "(无结果)"],
    "th": ["เรียกใช้เครื่องมือไม่สำเร็จ ({tool}): {detail}", "ชื่อเครื่องมือไม่ถูกต้อง: {tool}", "ไม่รู้จักเซิร์ฟเวอร์ MCP: {server}", "[ผลลัพธ์รูปภาพ]", "ข้อผิดพลาดที่ไม่ทราบสาเหตุ", "(ไม่มีผลลัพธ์)"],
    "vi": ["Thực thi công cụ thất bại ({tool}): {detail}", "Tên công cụ không hợp lệ: {tool}", "Máy chủ MCP không xác định: {server}", "[Kết quả hình ảnh]", "Lỗi không xác định", "(Không có kết quả)"],
    "es": ["Error al ejecutar la herramienta ({tool}): {detail}", "Nombre de herramienta no válido: {tool}", "Servidor MCP desconocido: {server}", "[Resultado de imagen]", "Error desconocido", "(Sin resultado)"],
    "fr": ["Échec de l’exécution de l’outil ({tool}) : {detail}", "Nom d’outil invalide : {tool}", "Serveur MCP inconnu : {server}", "[Résultat d’image]", "Erreur inconnue", "(Aucun résultat)"],
}
_KEYS = ("execution_failed", "invalid_name", "unknown_server", "image_result", "unknown_error", "no_result")
MESSAGES = {language: dict(zip(_KEYS, values)) for language, values in _MESSAGES.items()}


_NOT_OFFERED_MESSAGES = {
    "en": "Tool not offered in this request: {tool}",
    "ko": "이번 요청에 제공되지 않은 도구입니다: {tool}",
    "ja": "このリクエストで提供されていないツールです: {tool}",
    "zh": "本次请求未提供此工具：{tool}",
    "th": "เครื่องมือที่ไม่ได้ให้ไว้ในคำขอนี้: {tool}",
    "vi": "Công cụ không được cung cấp trong yêu cầu này: {tool}",
    "es": "Herramienta no ofrecida en esta solicitud: {tool}",
    "fr": "Outil non proposé dans cette requête : {tool}",
}
for _language, _message in _NOT_OFFERED_MESSAGES.items():
    MESSAGES[_language]["not_offered"] = _message


_WEB_SEARCH_MESSAGES = {
    'en': ['Check your Tavily API key in AI Tools settings.', 'The Tavily request or usage limit has been reached. Check your account usage.', 'Web search failed. Please try again later.', 'Enter a search query of 1–400 characters.'],
    'ko': ['AI 도구 설정에서 Tavily API 키를 확인하세요.', 'Tavily 요청 또는 사용 한도에 도달했습니다. 계정 사용량을 확인하세요.', '웹 검색에 실패했습니다. 잠시 후 다시 시도하세요.', '검색어는 1~400자로 입력하세요.'],
    'ja': ['AIツール設定でTavily APIキーを確認してください。', 'Tavilyのリクエストまたは使用量の上限に達しました。アカウントの使用量を確認してください。', 'ウェブ検索に失敗しました。後でもう一度お試しください。', '検索語は1～400文字で入力してください。'],
    'zh': ['请在 AI 工具设置中检查 Tavily API 密钥。', '已达到 Tavily 请求或使用限额。请检查账户用量。', '网页搜索失败。请稍后重试。', '请输入 1 至 400 个字符的搜索词。'],
    'es': ['Comprueba tu clave API de Tavily en los ajustes de herramientas de IA.', 'Se ha alcanzado el límite de solicitudes o uso de Tavily. Revisa el uso de tu cuenta.', 'La búsqueda web ha fallado. Inténtalo más tarde.', 'Introduce una consulta de entre 1 y 400 caracteres.'],
    'fr': ['Vérifiez votre clé API Tavily dans les paramètres des outils IA.', 'La limite de requêtes ou d’utilisation de Tavily est atteinte. Vérifiez votre consommation.', 'La recherche web a échoué. Réessayez plus tard.', 'Saisissez une recherche de 1 à 400 caractères.'],
    'vi': ['Kiểm tra khóa API Tavily trong cài đặt công cụ AI.', 'Đã đạt giới hạn yêu cầu hoặc sử dụng Tavily. Kiểm tra mức sử dụng tài khoản.', 'Tìm kiếm web thất bại. Vui lòng thử lại sau.', 'Nhập truy vấn tìm kiếm từ 1 đến 400 ký tự.'],
    'th': ['ตรวจสอบคีย์ API ของ Tavily ในการตั้งค่าเครื่องมือ AI', 'ถึงขีดจำกัดคำขอหรือการใช้งาน Tavily แล้ว โปรดตรวจสอบการใช้งานบัญชี', 'ค้นหาเว็บไม่สำเร็จ โปรดลองอีกครั้งภายหลัง', 'ป้อนคำค้นหาความยาว 1–400 ตัวอักษร'],
}
for _language, _values in _WEB_SEARCH_MESSAGES.items():
    MESSAGES[_language].update(zip(("web_search_key", "web_search_limit", "web_search_failed", "web_search_query"), _values))

async def get_tool_language() -> str:
    try:
        return await load_ui_language_async() or "en"
    except Exception:
        return "en"


def tool_message(key: str, language: str = "en", **params) -> str:
    code = (language or "en").replace("_", "-").split("-", 1)[0].lower()
    return MESSAGES.get(code, MESSAGES["en"])[key].format(**params)


def tool_error(message: str) -> str:
    # Machine-readable failure status must not depend on translated text.
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)
