# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from agent.tools import PlaywrightTools

# Crea l'applicazione Flask
app = Flask(__name__)
CORS(app)

# Istanza globale dei tool (per mantenere lo stato del browser)
playwright_tools = PlaywrightTools()

# ==================== ENDPOINT ESISTENTI ====================

@app.route('/')
def home():
    return jsonify({
        "message": "Server Python funziona!",
        "status": "online",
        "version": "1.0.0"
    })

@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "AI Test Automation Backend"
    })

@app.route('/api/test')
def test():
    return jsonify({
        "message": "Test endpoint funzionante!",
        "data": {
            "python_version": "3.12.10",
            "flask_version": "3.1.2"
        }
    })

# ==================== NUOVI ENDPOINT PLAYWRIGHT ====================

@app.route('/api/browser/start', methods=['POST'])
def start_browser():
    """
    Avvia il browser Chromium
    
    Body JSON (opzionale):
    {
        "headless": true  // false per vedere il browser
    }
    """
    try:
        data = request.get_json() or {}
        headless = data.get('headless', False)
        
        result = playwright_tools.start_browser(headless=headless)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/browser/navigate', methods=['POST'])
def navigate():
    """
    Naviga a un URL
    
    Body JSON:
    {
        "url": "https://google.com"
    }
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL mancante nel body"
            }), 400
        
        url = data['url']
        result = playwright_tools.navigate_to_url(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/browser/screenshot', methods=['GET'])
def screenshot():
    """
    Cattura screenshot della pagina corrente
    """
    try:
        result = playwright_tools.capture_screenshot()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/browser/info', methods=['GET'])
def page_info():
    """
    Ottiene info sulla pagina corrente
    """
    try:
        result = playwright_tools.get_page_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/browser/close', methods=['POST'])
def close_browser():
    """
    Chiude il browser
    """
    try:
        result = playwright_tools.close_browser()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ==================== ENDPOINT TUTTO IN UNO (per test rapidi) ====================

@app.route('/api/test-navigation', methods=['POST'])
def test_navigation():
    """
    Test completo: avvia browser -> naviga -> screenshot -> chiudi
    
    Body JSON:
    {
        "url": "https://google.com",
        "headless": true
    }
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL mancante"
            }), 400
        
        url = data['url']
        headless = data.get('headless', True)
        
        steps = []
        
        # 1. Avvia browser
        result = playwright_tools.start_browser(headless=headless)
        steps.append({"step": "start_browser", "result": result})
        
        if result['status'] != 'success':
            return jsonify({
                "status": "error",
                "message": "Errore nell'avviare il browser",
                "steps": steps
            }), 500
        
        # 2. Naviga
        result = playwright_tools.navigate_to_url(url)
        steps.append({"step": "navigate", "result": result})
        
        if result['status'] != 'success':
            playwright_tools.close_browser()
            return jsonify({
                "status": "error",
                "message": "Errore nella navigazione",
                "steps": steps
            }), 500
        
        # 3. Screenshot
        result = playwright_tools.capture_screenshot()
        steps.append({"step": "screenshot", "result": result})
        
        # 4. Chiudi browser
        close_result = playwright_tools.close_browser()
        steps.append({"step": "close_browser", "result": close_result})
        
        return jsonify({
            "status": "success",
            "message": f"Test completato per {url}",
            "steps": steps
        })
        
    except Exception as e:
        # Assicurati di chiudere il browser in caso di errore
        playwright_tools.close_browser()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ==================== AVVIO SERVER ====================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("SERVER AI TEST AUTOMATION")
    print("=" * 50)
    print("URL: http://localhost:5000")
    print("Endpoints disponibili:")
    print("   [Esistenti]")
    print("   - GET  /")
    print("   - GET  /api/health")
    print("   - GET  /api/test")
    print("\n   [Playwright - Step by Step]")
    print("   - POST /api/browser/start")
    print("   - POST /api/browser/navigate")
    print("   - GET  /api/browser/screenshot")
    print("   - GET  /api/browser/info")
    print("   - POST /api/browser/close")
    print("\n   [Playwright - Test Completo]")
    print("   - POST /api/test-navigation")
    print("=" * 50)
    print("Premi CTRL+C per fermare il server")
    print("=" * 50 + "\n")
    
    app.run(debug=True, port=5000)