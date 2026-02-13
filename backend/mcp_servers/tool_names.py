# Lista canonica dei tool esposti da questo MCP server
# (source of truth per logging e /api/mcp/info)
TOOL_NAMES = [
    "start_browser",
    "navigate_to_url",
    "wait_for_load_state",
    "capture_screenshot",
    "close_browser",
    "get_page_info",
    "wait_for_element",
    "get_text",
    "press_key",
    "inspect_interactive_elements",
    "handle_cookie_banner",
    "click_smart",
    "fill_smart",
    "wait_for_text_content",
    # "inspect_dom_changes",  # DEBUG ONLY - rimosso per evitare confusione AI
    # Procedural tools
    "get_frame",
    # "fill_and_search"  # DEPRECATED - use fill_smart + wait_for_text_content
]