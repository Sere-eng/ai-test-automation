# AI Test Automation con LLM, MCP e Playwright

Sistema di **test automation intelligente** che usa:
- **LLM (GPT‑4o, Claude, Gemini, …)** per capire test scritti in linguaggio naturale  
- **MCP (Model Context Protocol)** per orchestrare tool esterni in modo sicuro  
- **Playwright (async)** per pilotare il browser su **app enterprise Angular**

L’obiettivo è avere un **tester virtuale** che, dato un requisito funzionale in italiano/inglese, sia in grado di:
1. capire cosa fare,
2. navigare l’applicazione web,
3. eseguire i passi UI,
4. verificare i risultati attesi,
5. restituire un report strutturato (JSON + screenshot).

---

## 🎯 Cosa dimostra questo progetto

- **Automazione guidata da linguaggio naturale**  
  Esempio:  
  > “Avvia il browser, fai login su LAB, seleziona *organizzazione di sistema*, apri *Laboratory* e crea un nuovo filtro salvato.”

- **Architettura moderna “agentic”**  
  - LLM come cervello decisionale (ReAct, LangGraph)
  - Tool MCP Playwright come “mani” che cliccano, scrivono, aspettano
  - Design pronto per evolvere verso **workflow + multi‑agent** (più deterministico)

- **Automazione su app enterprise reale**  
  - Sistemi AMC / LAB con:
    - login SSO
    - iframe, componenti Angular Material
    - dashboard con contatori, filtri, card KPI
  - Scenari concreti:
    - creazione/salvataggio filtri
    - navigazione tramite contatori
    - elenco campioni e pagina dettaglio

- **Best practice anti‑allucinazioni**  
  - Discovery‑first: prima `inspect_interactive_elements`, poi `click_smart`/`fill_smart`
  - Niente selettori indovinati (`#username` & co.)
  - Regole di sistema prompt rigide per:
    - gestione errori
    - uso corretto dei tool
    - divieto di stringhe generiche tipo `"home"` per i check

---

## 🧱 Architettura ad alto livello

User / Tester
   |
   |  (HTTP JSON: test_description)
   v
Flask API  ───────────────► LangGraph Agent (ReAct)
                        (LLM multi‑provider: OpenRouter / OpenAI / Azure)
   |                                  |
   |                                  | MCP Protocol
   |                                  v
   |                       MCP Client (langchain-mcp-adapters)
   |                                  |
   |                                  | stdio / HTTP
   v                                  v
JSON response                MCP Server Playwright (async)
                           (21+ tool: navigate, inspect, click_smart, fill_smart, ...)
                                     |
                                     v
                               Chromium Headless
