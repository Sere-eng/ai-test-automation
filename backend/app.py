# backend/app.py
"""
Flask API Server per AI Test Automation con MCP.
Espone endpoint REST per l'AI Agent MCP e i tool Playwright.
"""

import re
import traceback
from pathlib import Path
from flask import (
    Flask,
    jsonify,
    request,
    Response,
    stream_with_context,
    send_from_directory,
)
from flask_cors import CORS

# from agent.tools import PlaywrightTools
from config.settings import AppConfig
import json
import asyncio
from datetime import datetime
import queue
import threading

from agent.utils import make_json_serializable
import subprocess
import tempfile
import os

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
    from agent.orchestrator import run_full_sync, run_prefix_to_home, run_lab_scenario
    from agent.lab_scenarios import LAB_SCENARIOS
    from codegen.script_generator import generate_playwright_script

    test_agent_mcp = TestAgentMCP()
    AGENT_MCP_AVAILABLE = True
    ORCHESTRATOR_AVAILABLE = True
    print(" AI Agent MCP e orchestrator caricati con successo!")
except ImportError as e:
    print(f" AI Agent MCP non disponibile: {e}")
    print("   Installare: pip install mcp langchain-mcp-adapters")
    test_agent_mcp = None
    run_full_sync = None
    run_prefix_to_home = None
    run_lab_scenario = None
    LAB_SCENARIOS = []
    ORCHESTRATOR_AVAILABLE = False

# ==================== ENDPOINT BASE ====================


@app.route("/")
def home():
    """Serve the HTML UI"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api")
def api_info():
    """API server information"""
    return jsonify(
        {
            "message": "AI Test Automation Server (MCP Edition)",
            "status": "online",
            "version": "2.0.0-mcp",
            "features": {
                "playwright_tools": "via_mcp",
                "direct_browser_endpoints": "disabled",
                "ai_agent_mcp": AGENT_MCP_AVAILABLE,
                "mcp_protocol": "1.12.3",
            },
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": "AI Test Automation Backend (MCP)",
            "playwright_tools": "via_mcp",
            "direct_browser_endpoints": "disabled",
            "agent_mcp": "ready" if AGENT_MCP_AVAILABLE else "not_available",
        }
    )


# ==================== ENDPOINT PLAYWRIGHT DIRETTI ====================
# Questi endpoint chiamano direttamente i tool Playwright
# (senza passare per MCP - utile per testing diretto)


@app.route("/api/browser/start", methods=["POST"])
def start_browser():
    """Avvia il browser Chromium"""
    try:
        return (
            jsonify(
                {
                    "status": "disabled",
                    "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP.",
                }
            ),
            410,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/browser/navigate", methods=["POST"])
def navigate():
    """Naviga a un URL"""
    try:
        return (
            jsonify(
                {
                    "status": "disabled",
                    "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP.",
                }
            ),
            410,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/browser/screenshot", methods=["GET"])
def screenshot():
    """Cattura screenshot"""
    try:
        return (
            jsonify(
                {
                    "status": "disabled",
                    "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP.",
                }
            ),
            410,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/browser/close", methods=["POST"])
def close_browser():
    """Chiude il browser"""
    try:
        return (
            jsonify(
                {
                    "status": "disabled",
                    "message": "This endpoint is disabled. Use /api/agent/mcp/test/run via MCP.",
                }
            ),
            410,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== ENDPOINT AI AGENT MCP ====================


@app.route("/api/agent/mcp/test/run", methods=["POST"])
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
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "AI Agent MCP non disponibile. Installare: pip install mcp langchain-mcp-adapters",
                }
            ),
            503,
        )

    try:
        data = request.get_json()
        if not data or "test_description" not in data:
            return (
                jsonify({"status": "error", "message": "test_description mancante"}),
                400,
            )

        test_description = data["test_description"]

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
                    if hasattr(output, "content"):
                        output = output.content
                        print(f"    Extracted .content from ToolMessage")

                    # L'output può essere una stringa JSON, devi parsarla!
                    if isinstance(output, str):
                        try:
                            import json

                            output = json.loads(output)
                            print(
                                f"    ✅ JSON parsed: keys={list(output.keys()) if isinstance(output, dict) else 'NOT_DICT'}"
                            )
                        except Exception as e:
                            print(f"    ❌ JSON parse failed: {e}")
                            continue

                    if isinstance(output, dict) and "base64" in output:
                        screenshot_base64 = output.get("base64")
                        print(
                            f"✅ Screenshot base64 trovato: {len(screenshot_base64)} caratteri"
                        )
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
            "timestamp": datetime.now().isoformat(),
        }

        # Non estrarre base64 da all_messages perché LangGraph satura il numero di token!
        # Se l'utente vuole base64, deve chiederlo esplicitamente nel test
        # e l'AI lo includerà nel final_answer

        return jsonify(response_data)

    except Exception as e:
        import traceback

        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@app.route("/api/agent/mcp/test/stream", methods=["GET"])
def agent_mcp_stream_test():
    """
    Stream del test in tempo reale via MCP (Server-Sent Events)

    Query params:
    ?description=Go to google.com
    &use_remote=false
    """
    if not AGENT_MCP_AVAILABLE:
        return (
            jsonify({"status": "error", "message": "AI Agent MCP non disponibile"}),
            503,
        )

    test_description = request.args.get("description")
    if not test_description:
        return jsonify({"status": "error", "message": "description mancante"}), 400

    use_remote = request.args.get("use_remote", "false").lower() == "true"

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
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ==================== ENDPOINT INFO MCP ====================


@app.route("/api/mcp/info", methods=["GET"])
def mcp_info():
    """Informazioni sulla configurazione MCP"""
    if not AGENT_MCP_AVAILABLE:
        return (
            jsonify({"status": "unavailable", "message": "MCP Agent not loaded"}),
            503,
        )

    return jsonify(
        {
            "status": "available",
            "mcp_version": "1.12.3",
            "current_mode": "remote" if test_agent_mcp.use_remote else "local",
            "config_mode": AppConfig.MCP.MODE,
            "servers": {
                "local": {"transport": "stdio", "status": "ready"},
                "remote": {
                    "transport": "streamable_http",
                    "url": AppConfig.MCP.get_remote_url(),
                    "status": "requires_manual_start",
                },
            },
            "tools_count": (
                len(test_agent_mcp.tool_names) if test_agent_mcp.tool_names else 13
            ),
            "tools": [
                "start_browser",
                "navigate_to_url",
                "click_element",
                "fill_input",
                "get_text",
                "check_element_exists",
                "press_key",
                "capture_screenshot",
                "close_browser",
                "get_page_info",
                "inspect_page_structure",
                "handle_cookie_banner",
            ],
        }
    )


# ==================== ENDPOINT LAB ORCHESTRATOR (agentico) ====================


@app.route("/api/test/lab/full", methods=["POST"])
def test_lab_full():
    """
    Esegue il flusso agentico LAB: Prefix Agent (login → home) + Dashboard Agent (scenario).

    Body JSON minimo:
    {
        "scenario_id": "scenario_1" | "scenario_2" | "scenario_3" | "scenario_4"
    }

    Body JSON opzionale (override URL/credenziali, generazione script):
    {
        "scenario_id": "...",
        "url": "...",
        "username": "...",
        "password": "...",
        "generate_script": true
    }
    Se generate_script=true e il run passa, lo script Playwright viene generato
    dalla trace sia del prefix che dello scenario (login dalla strategia MCP).
    """
    if not ORCHESTRATOR_AVAILABLE or run_full_sync is None:
        return (
            jsonify({"status": "error", "message": "Orchestrator non disponibile"}),
            503,
        )

    try:
        data = request.get_json() or {}
        scenario_id = data.get("scenario_id") or request.args.get("scenario_id")
        if not scenario_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "scenario_id mancante",
                        "available_scenarios": [s.id for s in LAB_SCENARIOS],
                    }
                ),
                400,
            )

        # Parametri opzionali per override di URL/credenziali LAB (possono venire dal frontend)
        lab_url = data.get("url") or data.get("lab_url") or request.args.get("url")
        lab_username = (
            data.get("username")
            or data.get("lab_username")
            or request.args.get("username")
        )
        lab_password = (
            data.get("password")
            or data.get("lab_password")
            or request.args.get("password")
        )

        result = run_full_sync(
            scenario_id,
            verbose=True,
            url=lab_url,
            user=lab_username,
            password=lab_password,
        )
        response_body = {
            "status": "success",
            "passed": result.get("passed", False),
            "phase": result.get("phase"),
            "prefix": result.get("prefix"),
            "scenario": result.get("scenario"),
            "errors": result.get("errors", []),
            "artifacts": result.get("artifacts", []),
            "duration_ms": result.get("duration_ms"),
        }
        generate_script = bool(data.get("generate_script", False))
        if generate_script and result.get("passed", False) and result.get("scenario"):
            try:
                script = generate_playwright_script(
                    scenario_result=result["scenario"],
                    scenario_id=scenario_id,
                    scenario_name=result["scenario"].get("scenario_name", scenario_id),
                    prefix_result=result.get("prefix"),
                )
                response_body["playwright_script"] = script or ""
            except Exception as e:
                response_body["playwright_script"] = None
                response_body["codegen_error"] = str(e)
        return jsonify(response_body)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/test/lab/prefix", methods=["POST"])
def test_lab_prefix():
    """
    Esegue solo il Prefix Agent LAB: login → selezione organizzazione → Continua → ingresso nel modulo Laboratory.

    Body JSON opzionale:
    {
        "url": "https://mdrsanitalab2.eng.it/multimodule/ELLIPSE_LAB/...",
        "username": "user_esterno",
        "password": "pwd_esterna"
    }

    Se i parametri non sono forniti, vengono usati quelli da AppConfig.LAB (es. da .env).
    """
    if not ORCHESTRATOR_AVAILABLE or run_prefix_to_home is None:
        return (
            jsonify({"status": "error", "message": "Orchestrator non disponibile"}),
            503,
        )

    try:
        data = request.get_json() or {}

        lab_url = data.get("url") or data.get("lab_url") or request.args.get("url")
        lab_username = (
            data.get("username")
            or data.get("lab_username")
            or request.args.get("username")
        )
        lab_password = (
            data.get("password")
            or data.get("lab_password")
            or request.args.get("password")
        )

        # Esegue SOLO il prefix (login → org → Continua → Laboratorio Analisi)
        # Il browser resta aperto per eventuale uso successivo.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        prefix_result = loop.run_until_complete(
            run_prefix_to_home(
                verbose=True,
                url=lab_url,
                user=lab_username,
                password=lab_password,
            )
        )
        loop.close()

        # Sanitize per evitare 500 (steps/result possono contenere oggetti non serializzabili)
        safe_result = make_json_serializable(prefix_result)
        return jsonify(
            {
                "status": "success",
                "phase": safe_result.get("phase", "prefix"),
                "passed": safe_result.get("passed", False),
                "result": safe_result,
                "errors": safe_result.get("errors", []),
                "artifacts": safe_result.get("artifacts", []),
                "duration_ms": safe_result.get("duration_ms"),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/test/lab/run", methods=["POST"])
def test_lab_run_scenario():
    """
    Esegue SOLO lo scenario LAB partendo dalla pagina attuale del browser (es. Preanalitica).

    Usare dopo POST /api/test/lab/prefix: il prefix lascia il browser aperto nel modulo Laboratory
    (tipicamente su Preanalitica); questa chiamata esegue lo scenario senza rifare login.

    Body JSON:
    {
        "scenario_id": "scenario_1" | "scenario_2" | "scenario_3" | "scenario_4",
        "generate_script": true | false
    }
    """
    if not ORCHESTRATOR_AVAILABLE or run_lab_scenario is None:
        return (
            jsonify({"status": "error", "message": "Orchestrator non disponibile"}),
            503,
        )

    data = request.get_json() or {}
    scenario_id = data.get("scenario_id") or request.args.get("scenario_id")
    generate_script = bool(data.get("generate_script", False))
    if not scenario_id:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "scenario_id mancante",
                    "available_scenarios": [s.id for s in LAB_SCENARIOS],
                }
            ),
            400,
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scenario_result = loop.run_until_complete(
        run_lab_scenario(scenario_id=scenario_id, verbose=True)
    )
    loop.close()

    safe_result = make_json_serializable(scenario_result)
    response_body = {
        "status": "success",
        "phase": safe_result.get("phase", "scenario"),
        "passed": safe_result.get("passed", False),
        "result": safe_result,
        "scenario_id": scenario_id,
    }

    if generate_script and safe_result.get("passed", False):
        try:
            script = generate_playwright_script(
                scenario_result=scenario_result,
                scenario_id=scenario_id,
                scenario_name=scenario_result.get("scenario_name", scenario_id),
            )
            response_body["playwright_script"] = script or ""
        except Exception as e:
            response_body["playwright_script"] = None
            response_body["codegen_error"] = str(e)

    return jsonify(response_body)


@app.route("/api/test/lab/scenarios", methods=["GET"])
def test_lab_scenarios_list():
    """Elenco scenari LAB disponibili per l'orchestrator."""
    if not ORCHESTRATOR_AVAILABLE:
        return jsonify({"status": "unavailable", "scenarios": []}), 503
    return jsonify(
        {
            "status": "ok",
            "scenarios": [
                {
                    "id": s.id,
                    "name": s.name,
                    "execution_steps": s.execution_steps,
                    "expected_results": s.expected_results,
                }
                for s in LAB_SCENARIOS
            ],
        }
    )


# ==================== ENDPOINT PLAYWRIGHT SCRIPT RUNNER ====================


@app.route("/api/test/playwright/run", methods=["POST"])
def run_playwright_script():
    """
    Esegue uno script Playwright Python (async pytest) passato dal frontend.

    Body JSON:
    {
        "script": "<contenuto file .py>",
        "scenario_id": "scenario_1"   # opzionale, solo per naming
    }
    """
    data = request.get_json() or {}
    script = data.get("script")
    scenario_id = data.get("scenario_id", "scenario")

    if not script:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "script mancante nel body",
                }
            ),
            400,
        )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = f"test_{scenario_id}.py"
            path = os.path.join(tmpdir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(script)

            # Esegue pytest in modo isolato nella cartella temporanea
            proc = subprocess.run(
                ["pytest", path, "-q"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )

            status = "success" if proc.returncode == 0 else "error"
            return jsonify(
                {
                    "status": status,
                    "return_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "filename": filename,
                }
            )
    except FileNotFoundError as e:
        # pytest non trovato / non installato
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "pytest non trovato. Assicurati che sia installato nel venv.",
                    "detail": str(e),
                }
            ),
            500,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# ==================== ENDPOINT DOCUMENT PROCESSING & BATCH TEST ====================

@app.route('/api/test/upload', methods=['POST'])
def upload_test_document():
    """
    Upload di un documento di test (Word, HTML, Excel, CSV).
    Il file viene salvato in data/test-cases/.
    """
    if 'file' not in request.files:
        return jsonify({
            "status": "error",
            "message": "Nessun file fornito. Usa 'file' come nome campo multipart."
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            "status": "error",
            "message": "Nessun file selezionato"
        }), 400
    
    # Verifica estensione
    allowed_extensions = {'.doc', '.docx', '.html', '.htm', '.xlsx', '.xls', '.csv'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return jsonify({
            "status": "error",
            "message": f"Formato non supportato. Formati accettati: {', '.join(allowed_extensions)}"
        }), 400
    
    # Salva file
    upload_dir = Path("data/test-cases")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = upload_dir / file.filename
    file.save(str(filepath))
    
    return jsonify({
        "status": "success",
        "message": "File caricato con successo",
        "filename": file.filename,
        "path": str(filepath),
        "size_bytes": filepath.stat().st_size
    })


@app.route('/api/test/extract-scenarios', methods=['POST'])
def extract_scenarios_from_document():
    """
    Estrae scenari da un documento di test usando LLM.
    
    Body JSON:
    {
        "file": "nome_file.doc"  (file in data/test-cases/)
        oppure
        "filepath": "/path/assoluto/al/file"
    }
    
    Returns: Lista di scenari estratti
    """
    try:
        from agent.document_parser import parse_test_document
        from agent.scenario_extractor import extract_scenarios_from_document, scenarios_to_dict
    except ImportError as e:
        return jsonify({
            "status": "error",
            "message": f"Moduli non disponibili: {e}. Installa: pip install beautifulsoup4 chardet"
        }), 503
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Body JSON richiesto"
        }), 400
    
    # Determina filepath
    if 'filepath' in data:
        filepath = data['filepath']
    elif 'file' in data:
        filepath = str(Path("data/test-cases") / data['file'])
    else:
        return jsonify({
            "status": "error",
            "message": "Specificare 'file' o 'filepath'"
        }), 400
    
    if not Path(filepath).exists():
        return jsonify({
            "status": "error",
            "message": f"File non trovato: {filepath}"
        }), 404
    
    try:
        print(f"📄 Inizio parsing del file: {filepath}")
        
        # 1. Parse documento
        parsed = parse_test_document(filepath)
        
        print(f"✓ Parsing completato - Formato: {parsed.get('format')}")
        
        # 2. Se è un file Excel/CSV con test_cases già strutturati, convertili direttamente
        if 'test_cases' in parsed:
            print(f"📊 File Excel/CSV rilevato - Conversione diretta dei test case")
            # File Excel/CSV con casi di test strutturati
            scenarios = []
            for i, test_case in enumerate(parsed.get('test_cases', [])):
                scenario = {
                    'id': f"test_case_{i+1}",
                    'name': test_case.get('objective', f"Test Case {i+1}"),
                    'prerequisites': test_case.get('prerequisites', ''),
                    'input_data': test_case.get('input_data', ''),
                    'execution_steps': [test_case.get('description', '')],
                    'expected_results': [test_case.get('expected_results', '')],
                    'row_number': test_case.get('row_number')
                }
                scenarios.append(scenario)
                if (i + 1) % 5 == 0:
                    print(f"  → Convertiti {i + 1}/{len(parsed.get('test_cases', []))} test case")
            
            print(f"✅ Conversione completata: {len(scenarios)} scenari estratti")
            
            return jsonify({
                "status": "success",
                "document": {
                    "title": parsed.get('title'),
                    "format": parsed.get('format'),
                    "test_cases_count": parsed.get('test_cases_count')
                },
                "scenarios_count": len(scenarios),
                "scenarios": scenarios
            })
        else:
            print(f"📝 File Word/HTML rilevato - Estrazione con LLM")
            # File Word/HTML - usa LLM per estrazione
            scenarios = extract_scenarios_from_document(parsed)
            
            print(f"✅ Estrazione LLM completata: {len(scenarios)} scenari")
            
            return jsonify({
                "status": "success",
                "document": {
                    "title": parsed.get('title'),
                    "format": parsed.get('format')
                },
                "scenarios_count": len(scenarios),
                "scenarios": scenarios_to_dict(scenarios)
            })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/test/batch', methods=['POST'])
def run_batch_test():
    """
    Esegue batch test di scenari LAB.
    
    Body JSON:
    {
        "scenarios": [  // Lista di scenari (come dict o solo ID)
            {"id": "scenario_1", "name": "...", "execution_steps": [...], "expected_results": [...]},
            // oppure solo ID per scenari già definiti in lab_scenarios.py:
            "scenario_2"
        ],
        "url": "https://...",  // opzionale
        "username": "...",     // opzionale
        "password": "...",     // opzionale
        "save_results": true   // opzionale, default true
    }
    """
    if not ORCHESTRATOR_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Orchestrator non disponibile"
        }), 503
    
    try:
        from agent.batch_runner import run_batch_sync
        from agent.lab_scenarios import LabScenario, LAB_SCENARIOS
    except ImportError as e:
        return jsonify({
            "status": "error",
            "message": f"Batch runner non disponibile: {e}"
        }), 503
    
    data = request.get_json()
    
    if not data or 'scenarios' not in data:
        return jsonify({
            "status": "error",
            "message": "Body JSON richiesto con campo 'scenarios'"
        }), 400
    
    scenarios_input = data['scenarios']
    if not isinstance(scenarios_input, list) or not scenarios_input:
        return jsonify({
            "status": "error",
            "message": "'scenarios' deve essere una lista non vuota"
        }), 400
    
    # Converti scenari in LabScenario objects
    scenarios = []
    for item in scenarios_input:
        if isinstance(item, str):
            # È un ID, cerca negli scenari esistenti
            existing = next((s for s in LAB_SCENARIOS if s.id == item), None)
            if existing:
                scenarios.append(existing)
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Scenario ID '{item}' non trovato",
                    "available_scenarios": [s.id for s in LAB_SCENARIOS]
                }), 400
        elif isinstance(item, dict):
            # È un dict completo, crea LabScenario
            try:
                scenario = LabScenario(
                    id=item.get('id', f"dynamic_{len(scenarios) + 1}"),
                    name=item.get('name', 'Unnamed'),
                    execution_steps=item.get('execution_steps', []),
                    expected_results=item.get('expected_results', []),
                    prompt_hints=item.get('prompt_hints')
                )
                scenarios.append(scenario)
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Errore nella creazione scenario: {e}"
                }), 400
        else:
            return jsonify({
                "status": "error",
                "message": f"Formato scenario non valido: {type(item)}"
            }), 400
    
    # Parametri opzionali
    url = data.get('url')
    username = data.get('username')
    password = data.get('password')
    save_results = data.get('save_results', True)
    
    try:
        # Esegui batch (sincrono, bloccante)
        results = run_batch_sync(
            scenarios=scenarios,
            url=url,
            username=username,
            password=password,
            verbose=True,  # Non stampare in console per API
            save_results=save_results
        )
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/test/batch/stream', methods=['POST'])
def run_batch_test_stream():
    """
    Esegue batch test con streaming SSE per progress real-time.
    
    Body JSON: vedi run_batch_test() per formato
    
    Returns: Server-Sent Events stream con eventi:
    - scenario_start: inizio scenario
    - phase_update: cambio fase (prefix/scenario)
    - step_update: completamento step
    - scenario_complete: fine scenario
    - batch_complete: fine batch
    - error: errore durante esecuzione
    """
    if not ORCHESTRATOR_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Orchestrator non disponibile"
        }), 503
    
    try:
        from agent.batch_runner import BatchTestRunner
        from agent.lab_scenarios import LabScenario, LAB_SCENARIOS
    except ImportError as e:
        return jsonify({
            "status": "error",
            "message": f"Batch runner non disponibile: {e}"
        }), 503
    
    data = request.get_json()
    
    if not data or 'scenarios' not in data:
        return jsonify({
            "status": "error",
            "message": "Body JSON richiesto con campo 'scenarios'"
        }), 400
    
    scenarios_input = data['scenarios']
    if not isinstance(scenarios_input, list) or not scenarios_input:
        return jsonify({
            "status": "error",
            "message": "'scenarios' deve essere una lista non vuota"
        }), 400
    
    # Converti scenari in LabScenario objects
    scenarios = []
    for item in scenarios_input:
        if isinstance(item, str):
            existing = next((s for s in LAB_SCENARIOS if s.id == item), None)
            if existing:
                scenarios.append(existing)
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Scenario ID '{item}' non trovato"
                }), 400
        elif isinstance(item, dict):
            try:
                scenario = LabScenario(
                    id=item.get('id', f"dynamic_{len(scenarios) + 1}"),
                    name=item.get('name', 'Unnamed'),
                    execution_steps=item.get('execution_steps', []),
                    expected_results=item.get('expected_results', []),
                    prompt_hints=item.get('prompt_hints')
                )
                scenarios.append(scenario)
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Errore nella creazione scenario: {e}"
                }), 400
    
    url = data.get('url')
    username = data.get('username')
    password = data.get('password')
    save_results = data.get('save_results', True)
    
    # Crea una queue per gli eventi SSE
    event_queue = queue.Queue()
    
    def progress_callback(event_type: str, event_data: dict):
        """Callback chiamato dal BatchTestRunner per emettere eventi."""
        event_queue.put({
            'event': event_type,
            'data': event_data
        })
    
    def generate():
        """Generator function per SSE stream."""
        try:
            # Esegui batch in un thread separato
            runner = BatchTestRunner(
                url=url,
                username=username,
                password=password,
                progress_callback=progress_callback
            )
            
            results = {'error': None}
            
            def run_batch_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    batch_results = loop.run_until_complete(
                        runner.run_batch(scenarios, verbose=True)
                    )
                    
                    if save_results:
                        filepath = runner.save_results(batch_results)
                        batch_results['saved_to'] = filepath
                    
                    results['data'] = batch_results
                    
                    # Segnala fine
                    event_queue.put(None)
                    
                except Exception as e:
                    results['error'] = str(e)
                    event_queue.put(None)
            
            # Avvia thread
            thread = threading.Thread(target=run_batch_async)
            thread.start()
            
            # Stream eventi dalla queue
            while True:
                try:
                    event = event_queue.get(timeout=0.5)
                    
                    if event is None:
                        # Fine stream
                        if results.get('error'):
                            yield f"event: error\ndata: {json.dumps({'error': results['error']})}\n\n"
                        elif results.get('data'):
                            # Invia risultati finali
                            final_data = results['data']
                            yield f"event: batch_complete\ndata: {json.dumps(make_json_serializable(final_data))}\n\n"
                        break
                    
                    # Emetti evento SSE
                    event_type = event['event']
                    event_data = make_json_serializable(event['data'])
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                    
                except queue.Empty:
                    # Invia keepalive ogni 0.5s
                    yield f": keepalive\n\n"
                    continue
            
            thread.join(timeout=1)
            
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


# ==================== ENDPOINT AMC LOGIN ====================


@app.route("/api/test/amc/login", methods=["POST"])
def test_amc_login():
    """Test completo AMC: Login → Micrologistica → Anagrafiche → Causali (con discovery pattern)"""

    if not AGENT_MCP_AVAILABLE:
        return (
            jsonify({"status": "error", "message": "AI Agent MCP non disponibile"}),
            503,
        )

    if not AppConfig.AMC.validate():
        return (
            jsonify({"status": "error", "message": "AMC credentials non configurate"}),
            400,
        )

    try:
        data = {}
        if request.is_json:
            data = request.get_json() or {}

        take_screenshot = data.get("take_screenshot", False)

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
            pattern = r"SCREENSHOT_BASE64:\s*([A-Za-z0-9+/=]+)"
            matches = re.findall(pattern, result["final_answer"])

            for idx, base64_data in enumerate(matches):
                screenshots.append(
                    {
                        "filename": f"amc_causali_search_{idx+1}.png",
                        "base64": base64_data,
                        "size_bytes": len(base64_data) * 3 // 4,
                        "source": "ai_agent_response",
                    }
                )

        return jsonify(
            {
                "status": "success",
                "test_type": "amc_full_workflow",
                "username": AppConfig.AMC.USERNAME,
                "notes": result.get("notes", "Test executed"),
                "passed": result["passed"],
                "screenshots": screenshots,
                "screenshots_count": len(screenshots),
                "workflow": "Login → Micrologistica → Anagrafiche → Causali → Search 'carm'",
                "note": "Using discovery pattern with inspect_interactive_elements()",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        import traceback

        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@app.route("/api/test/amc/inspect", methods=["POST"])
def test_amc_inspect():
    """
    Ispeziona il form di login AMC per trovare selettori corretti.
    Utile per aggiornare i selettori in config/settings.py
    """
    if not AGENT_MCP_AVAILABLE:
        return (
            jsonify({"status": "error", "message": "AI Agent MCP non disponibile"}),
            503,
        )

    try:
        test_description = f"""
        Go to {AppConfig.AMC.URL}
        Wait 3 seconds for page to load
        Call inspect_page_structure to analyze the login form
        Close browser
        """

        print(f" Inspecting AMC login page structure...")
        result = test_agent_mcp.run_test(test_description, verbose=True)

        return jsonify(
            {
                "status": "success",
                "test_type": "amc_inspect",
                "final_answer": result["final_answer"],
                "note": "Use this info to update selectors in config/settings.py AMCConfig",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        import traceback

        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


# ==================== AVVIO SERVER ====================


if __name__ == "__main__":
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
        
        print("\n[DOCUMENT PROCESSING & BATCH TEST]")
        print("   - POST /api/test/upload           → Upload documento test (Word/HTML)")
        print("   - POST /api/test/extract-scenarios → Estrai scenari da documento (LLM)")
        print("   - POST /api/test/batch            → Esegui batch di scenari")
        print("   - GET  /api/test/lab/scenarios    → Lista scenari LAB disponibili")
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
        threaded=True,
    )
