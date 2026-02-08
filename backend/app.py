# backend/app.py
"""
Flask API Server per AI Test Automation con MCP.
Espone endpoint REST per l'AI Agent MCP e i tool Playwright.
"""

import re
from flask import Flask, jsonify, request, Response, stream_with_context, send_from_directory
from flask_cors import CORS
# from agent.tools import PlaywrightTools
from config.settings import AppConfig
import json
import asyncio
from datetime import datetime

# Valida configurazione all'avvio
AppConfig.validate_all()

# Crea l'applicazione Flask
app = Flask(__name__)
CORS(app)

# Istanza globale dei tool Playwright (per endpoint diretti)
# playwright_tools = PlaywrightTools()

# Flag per indicare se l'AI Agent MCP è disponibile
AGENT_MCP_AVAILABLE = False

# Prova a importare l'AI Agent MCP
try:
    from agent.test_agent_mcp import TestAgentMCP
    # Inizializza l'agent (verrà inizializzato alla prima chiamata)
    # IMPORTANTE: usa_remote=True per server HTTP remoto, parametro che prende da config
    # Assicurati che playwright_server_remote.py sia in esecuzione su porta 8001
    test_agent_mcp = TestAgentMCP()  # Usa remoto HTTP
    AGENT_MCP_AVAILABLE = True
    print(" AI Agent MCP caricato con successo!")
except ImportError as e:
    print(f" AI Agent MCP non disponibile: {e}")
    print("   Installare: pip install mcp langchain-mcp-adapters")
    test_agent_mcp = None

# ==================== ENDPOINT BASE ====================


@app.route('/')
def home():
    """Serve the HTML UI"""
    return send_from_directory(app.static_folder, "index.html")


@app.route('/api')
def api_info():
    """API server information"""
    return jsonify({
        "message": "AI Test Automation Server (MCP Edition)",
        "status": "online",
        "version": "2.0.0-mcp",
        "features": {
            "playwright_tools": "via_mcp",
            "direct_browser_endpoints": "disabled",
            "ai_agent_mcp": AGENT_MCP_AVAILABLE,
            "mcp_protocol": "1.12.3"
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "AI Test Automation Backend (MCP)",
        "playwright_tools": "via_mcp",
        "direct_browser_endpoints": "disabled",
        "agent_mcp": "ready" if AGENT_MCP_AVAILABLE else "not_available"
    })

# ==================== ENDPOINT PLAYWRIGHT DIRETTI ====================
# Questi endpoint chiamano direttamente i tool Playwright
# (senza passare per MCP - utile per testing diretto)


@app.route('/api/browser/start', methods=['POST'])
def start_browser():
    """Avvia il browser Chromium"""
    try:
        return jsonify({
            "status": "disabled",
            "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP."
        }), 410
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/browser/navigate', methods=['POST'])
def navigate():
    """Naviga a un URL"""
    try:
        return jsonify({
            "status": "disabled",
            "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP."
        }), 410
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/browser/screenshot', methods=['GET'])
def screenshot():
    """Cattura screenshot"""
    try:
        return jsonify({
            "status": "disabled",
            "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP."
        }), 410
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/browser/close', methods=['POST'])
def close_browser():
    """Chiude il browser"""
    try:
        return jsonify({
            "status": "disabled",
            "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP."
        }), 410
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== ENDPOINT AI AGENT MCP ====================


@app.route('/api/agent/mcp/test/run', methods=['POST'])
def agent_mcp_run_test():
    """
    Esegue un test usando l'AI Agent con MCP

    Body JSON:
    {
        "test_description": "Go to google.com and search for 'AI testing'"
    }

    Response include screenshots in base64!
    """
    if not AGENT_MCP_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Agent MCP non disponibile. Installare: pip install mcp langchain-mcp-adapters"
        }), 503

    try:
        data = request.get_json()
        if not data or 'test_description' not in data:
            return jsonify({
                "status": "error",
                "message": "test_description mancante"
            }), 400

        test_description = data['test_description']

        # Esegui il test con l'agent MCP (sincrono)
        result = test_agent_mcp.run_test(test_description, verbose=True)

        # Estrai base64 screenshot dagli steps (se presente)
        screenshot_base64 = None
        print(f"\n🔍 DEBUG: Cerco screenshot in {len(result.get('steps', []))} steps")
        
        for i, step in enumerate(result.get("steps", [])):
            # Debug ogni step
            if isinstance(step, dict):
                tool_name = step.get("tool", "NO_TOOL")
                print(f"  Step {i}: tool={tool_name}")
                
                if tool_name == "capture_screenshot":
                    output = step.get("output", {})
                    print(f"    output type: {type(output)}")
                    
                    # Se è un ToolMessage di LangChain, estrai il .content
                    if hasattr(output, 'content'):
                        output = output.content
                        print(f"    Extracted .content from ToolMessage")
                    
                    # L'output può essere una stringa JSON, devi parsarla!
                    if isinstance(output, str):
                        try:
                            import json
                            output = json.loads(output)
                            print(f"    ✅ JSON parsed: keys={list(output.keys()) if isinstance(output, dict) else 'NOT_DICT'}")
                        except Exception as e:
                            print(f"    ❌ JSON parse failed: {e}")
                            continue
                    
                    if isinstance(output, dict) and "base64" in output:
                        screenshot_base64 = output.get("base64")
                        print(f"✅ Screenshot base64 trovato: {len(screenshot_base64)} caratteri")
            else:
                print(f"  Step {i}: NOT A DICT - type={type(step)}")

        if not screenshot_base64:
            print("❌ Nessuno screenshot base64 trovato")

        response_data = {
            "status": "success",
            "run_id": result.get("run_id"),
            "final_answer": result.get("notes", ""),
            "passed": result.get("passed", False),
            "errors": result.get("errors", []),
            "artifacts": result.get("artifacts", []),
            "screenshot": screenshot_base64,
            "test_description": result["test_description"],
            "mcp_mode": AppConfig.MCP.MODE,
            "timestamp": datetime.now().isoformat()
        }

        # Non estrarre base64 da all_messages perché LangGraph satura il numero di token!
        # Se l'utente vuole base64, deve chiederlo esplicitamente nel test
        # e l'AI lo includerà nel final_answer

        return jsonify(response_data)

    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/agent/mcp/test/stream', methods=['GET'])
def agent_mcp_stream_test():
    """
    Stream del test in tempo reale via MCP (Server-Sent Events)

    Query params:
    ?description=Go to google.com
    &use_remote=false
    """
    if not AGENT_MCP_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Agent MCP non disponibile"
        }), 503

    test_description = request.args.get('description')
    if not test_description:
        return jsonify({
            "status": "error",
            "message": "description mancante"
        }), 400

    use_remote = request.args.get('use_remote', 'false').lower() == 'true'

    # Aggiorna configurazione se necessario
    if use_remote != test_agent_mcp.use_remote:
        test_agent_mcp.use_remote = use_remote
        test_agent_mcp._initialized = False

    async def stream_events():
        """Generator async per SSE"""
        try:
            async for event in test_agent_mcp.run_test_stream(test_description):
                # Converti evento in JSON string
                event_json = json.dumps(event, default=str)
                yield f"data: {event_json}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def generate():
        """Wrapper sincrono per il generator async"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async_gen = stream_events()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

# ==================== ENDPOINT INFO MCP ====================


@app.route('/api/mcp/info', methods=['GET'])
def mcp_info():
    """Informazioni sulla configurazione MCP"""
    if not AGENT_MCP_AVAILABLE:
        return jsonify({
            "status": "unavailable",
            "message": "MCP Agent not loaded"
        }), 503

    return jsonify({
        "status": "available",
        "mcp_version": "1.12.3",
        "current_mode": "remote" if test_agent_mcp.use_remote else "local",
        "config_mode": AppConfig.MCP.MODE,
        "servers": {
            "local": {
                "transport": "stdio",
                "status": "ready"
            },
            "remote": {
                "transport": "streamable_http",
                "url": AppConfig.MCP.get_remote_url(),
                "status": "requires_manual_start"
            }
        },
        "tools_count": len(test_agent_mcp.tool_names) if test_agent_mcp.tool_names else 13,
        "tools": [
            "start_browser", "navigate_to_url", "click_element",
            "fill_input", "wait_for_element", "get_text",
            "check_element_exists", "press_key", "capture_screenshot",
            "close_browser", "get_page_info", "inspect_page_structure",
            "handle_cookie_banner"
        ]
    })

# ==================== ENDPOINT AMC LOGIN ====================

@app.route('/api/test/amc/login', methods=['POST'])
def test_amc_login():
    """Test completo AMC: Login → Micrologistica → Anagrafiche → Causali (con discovery pattern)"""

    if not AGENT_MCP_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Agent MCP non disponibile"
        }), 503

    if not AppConfig.AMC.validate():
        return jsonify({
            "status": "error",
            "message": "AMC credentials non configurate"
        }), 400

    try:
        data = {}
        if request.is_json:
            data = request.get_json() or {}

        take_screenshot = data.get('take_screenshot', False)

        # WORKFLOW AMC - Natural language (AI decides tools based on system prompt)
        test_description = (
            f"Start the browser in non-headless mode and navigate to {AppConfig.AMC.URL}. "
            f"Wait for the page to fully load.\n"
            f"\n"
            f"Login to the application:\n"
            f"- Fill the username field with '{AppConfig.AMC.USERNAME}'\n"
            f"- Fill the password field with '{AppConfig.AMC.PASSWORD}'\n"
            f"- Submit the form by pressing the login button\n"
            f"- Wait for the page to load completely\n"
            f"\n"
            f"Navigate to Micrologistica:\n"
            f"- Find and click on the 'Micrologistica'\n"
            f"- Wait for the page to load\n"
            f"\n"
            f"Open the Anagrafiche section:\n"
            f"- Click on 'Anagrafiche' in the menu\n"
            f"- Wait for the submenu to appear\n"
            f"\n"
            f"Open Causali:\n"
            f"- Click on 'Causali' in the submenu\n"
            f"- Wait for the page to load\n"
            f"\n"
            f"Perform a search for 'carm' and verify results appear.\n"
            f"\n"
            f"Close the browser.\n"
        )

        result = test_agent_mcp.run_test(test_description, verbose=True)

        # Extract screenshots se presenti
        screenshots = []
        if take_screenshot:
            pattern = r'SCREENSHOT_BASE64:\s*([A-Za-z0-9+/=]+)'
            matches = re.findall(pattern, result["final_answer"])

            for idx, base64_data in enumerate(matches):
                screenshots.append({
                    "filename": f"amc_causali_search_{idx+1}.png",
                    "base64": base64_data,
                    "size_bytes": len(base64_data) * 3 // 4,
                    "source": "ai_agent_response"
                })

        return jsonify({
            "status": "success",
            "test_type": "amc_full_workflow",
            "username": AppConfig.AMC.USERNAME,
            "notes": result.get("notes", "Test executed"),
            "passed": result["passed"],
            "screenshots": screenshots,
            "screenshots_count": len(screenshots),
            "workflow": "Login → Micrologistica → Anagrafiche → Causali → Search 'carm'",
            "note": "Using discovery pattern with inspect_interactive_elements()",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/test/amc/inspect', methods=['POST'])
def test_amc_inspect():
    """
    Ispeziona il form di login AMC per trovare selettori corretti.
    Utile per aggiornare i selettori in config/settings.py
    """
    if not AGENT_MCP_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "AI Agent MCP non disponibile"
        }), 503

    try:
        test_description = f"""
        Go to {AppConfig.AMC.URL}
        Wait 3 seconds for page to load
        Call inspect_page_structure to analyze the login form
        Close browser
        """

        print(f" Inspecting AMC login page structure...")
        result = test_agent_mcp.run_test(test_description, verbose=True)

        return jsonify({
            "status": "success",
            "test_type": "amc_inspect",
            "final_answer": result["final_answer"],
            "note": "Use this info to update selectors in config/settings.py AMCConfig",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500

# ==================== AVVIO SERVER ====================


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("AI TEST AUTOMATION SERVER (MCP Edition)")
    print("=" * 80)
    print(f"URL: http://{AppConfig.FLASK.HOST}:{AppConfig.FLASK.PORT}")
    print(f"MCP Mode: {AppConfig.MCP.MODE}")

    print("\n ENDPOINT DISPONIBILI:")
    print("\n[BASE]")
    print("   - GET  /                      → Server info")
    print("   - GET  /api/health            → Health check")

    print("\n[BROWSER]")
    print("   - Direct endpoints: DISABLED (use MCP via AI Agent)")

    if AGENT_MCP_AVAILABLE:
        print("\n[AI AGENT MCP]")
        print("   - POST /api/agent/mcp/test/run    → Esegui test con AI+MCP")
        print("   - GET  /api/agent/mcp/test/stream → Stream test real-time")
        print("   - GET  /api/mcp/info              → Info configurazione MCP")
        print(f"\n   MCP Mode: {AppConfig.MCP.MODE.upper()}")
        if AppConfig.MCP.use_remote():
            print(f"      Server remoto: {AppConfig.MCP.get_remote_url()}")
            print("      (Assicurati che playwright_server_remote.py sia attivo)")
        else:
            print("      Server locale: stdio")

        print("\n[AMC LOGIN TEST]")
        print("   - POST /api/test/amc/inspect      → Ispeziona form login")
        print("   - POST /api/test/amc/login        → Test login automatico")

        if AppConfig.AMC.validate():
            print(f"  Credenziali configurate: {AppConfig.AMC.USERNAME}")
        else:
            print(
                f"  Credenziali NON configurate (aggiungi AMC_USERNAME/PASSWORD in .env)")
    else:
        print("\n[AI AGENT MCP] Non disponibile")
        print("   Installa: pip install mcp==1.12.3 langchain-mcp-adapters==0.1.7")

    print("\n" + "=" * 80)
    print("Premi CTRL+C per fermare il server")
    print("=" * 80 + "\n")

    app.run(
        host=AppConfig.FLASK.HOST,
        port=AppConfig.FLASK.PORT,
        debug=AppConfig.FLASK.DEBUG,
        threaded=True
    )
