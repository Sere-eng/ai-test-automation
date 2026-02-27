# Production-oriented agentic system for LLM-driven UI automation in complex enterprise environments.

Sistema di **test automation intelligente** che usa:
- **LLM (GPT-4o, Claude, Gemini, …)** per capire test scritti in linguaggio naturale
- **MCP (Model Context Protocol)** per orchestrare tool esterni in modo sicuro
- **Playwright (async)** per pilotare il browser su **app enterprise Angular**

L'obiettivo è avere un **tester virtuale** che, dato un requisito funzionale in italiano/inglese, sia in grado di:
1. capire cosa fare
2. navigare l'applicazione web
3. eseguire i passi UI
4. verificare i risultati attesi
5. restituire un report strutturato (JSON + screenshot)

---

## Cosa fa questo progetto

### Automazione guidata da linguaggio naturale

Il sistema riceve uno scenario scritto in linguaggio naturale, non pre-strutturato.

Esempio:

> "Login to LAB, open the Laboratory dashboard and create a new saved filter."

L’istruzione viene interpretata dall’LLM e scomposta in passi eseguibili.  
L’esecuzione avviene esclusivamente tramite tool MCP validati, senza accesso diretto al DOM o utilizzo di selettori hard-coded.

Pattern di esecuzione tipico:

1. `start_browser`
2. `navigate_to_url`
3. `inspect_interactive_elements` (discovery-first)
4. `click_smart` (fallback su ARIA role, accessible name, label, CSS validato)
5. `fill_smart` (solo campi obbligatori identificati dinamicamente)
6. `wait_for_dom_change`
7. validazione strutturata tramite `evaluation.py`

Il pass/fail è determinato in modo **deterministico** dai risultati dei tool (JSON strutturato), non dall’output testuale del modello.

---

### Automazione su app enterprise reale

Validato su moduli AMC / LAB in ambiente enterprise sanitario con:

- login SSO
- iframe annidati
- componenti Angular Material
- dashboard con contatori, card KPI, filtri dinamici

Scenari concreti includono:

- creazione e salvataggio di filtri
- navigazione tramite contatori
- apertura lista campioni e pagina dettaglio
- verifica presenza elementi post-azione

L’architettura è progettata per funzionare su interfacce non uniformi, dove non è possibile aggiungere attributi di test (no `data-testid`).

---

### Best practice anti-allucinazioni

- Discovery-first: prima `inspect_interactive_elements`, poi `click_smart` / `fill_smart`
- Nessun selettore inventato (`#username`, `#submit`, ecc.)
- Tool invocation obbligatoria per ogni azione
- Separazione netta tra:
  - reasoning LLM
  - esecuzione tool
  - valutazione deterministica
- Regole di system prompt rigide per gestione errori e divieto di stringhe generiche nei check (es. `"home"`, `"dashboard"`)

---

## Architettura

```
User / Tester
   │
   │  HTTP JSON { test_description }
   ▼
Flask API
   │
   ▼
Orchestrator (orchestrator.py)
   ├── Prefix Agent  → login → selezione org → tile Laboratory  (browser rimane aperto)
   └── Scenario Agent → esegue lo scenario LAB dalla dashboard  (chiude il browser)
         │
         │  LangGraph ReAct
         ▼
   LLM (OpenRouter / OpenAI / Azure)
         │
         │  MCP Protocol
         ▼
   MCP Client (langchain-mcp-adapters)
         │
         │  stdio | HTTP
         ▼
   MCP Server Playwright (async)
   21 tool: start_browser, navigate_to_url, inspect_interactive_elements,
            click_smart, fill_smart, wait_for_dom_change, inspect_region, …
         │
         ▼
   Chromium
         │
         ▼
JSON response + screenshot
```

Pass/fail deciso da `evaluation.py` sui tool results — non dall'output testuale del modello.

---

## Documentazione

| File | Contenuto |
|------|-----------|
| [`backend/README.md`](backend/README.md) | Setup, configurazione, API endpoints, riferimento completo ai tool |
| [`backend/agent/TOOLS.md`](backend/agent/TOOLS.md) | Guida operativa ai 21 tool Playwright MCP: input/output, pattern d'uso |
