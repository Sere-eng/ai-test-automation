# Lista canonica dei tool esposti dal MCP server (source of truth per logging e avvio).
# Include i tool di check per la regola "dopo ogni azione, un check esplicito".
TOOL_NAMES = [
    # RAW - lifecycle & pagina
    "start_browser",
    "close_browser",
    "navigate_to_url",
    "get_page_info",
    "capture_screenshot",

    # RAW - elementi, tastiera, load state, iframe
    "press_key",
    "get_text",
    "wait_for_element",
    "wait_for_load_state",
    "get_frame",

    # MEDIUM - check / wait su testo o presenza
    "wait_for_text_content",
    "check_element_exists",

    # SMART LOCATORS & INSPECTION
    "click_smart",
    "fill_smart",
    "inspect_interactive_elements",

    # ADVANCED - wait per nome / controlli / banner / step composti
    "wait_for_clickable_by_name",
    "wait_for_control_by_name_and_type",
    "wait_for_field_by_name",
    "handle_cookie_banner",
    "click_and_wait_for_text",
]