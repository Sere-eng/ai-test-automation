# backend/agent/scenario_extractor.py
"""
Scenario Extractor - Usa LLM per convertire documenti di test in scenari strutturati.
"""

import json
import re
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import LLMConfig
from agent.lab_scenarios import LabScenario


def get_llm_for_extraction():
    """Crea istanza LLM per estrazione scenari (usa stesse configurazioni di test agent)."""
    provider = LLMConfig.get_provider()
    
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLMConfig.OPENROUTER_MODEL,
            api_key=LLMConfig.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_tokens=4000,
        )
    elif provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_deployment=LLMConfig.AZURE_DEPLOYMENT,
            api_version=LLMConfig.AZURE_API_VERSION,
            azure_endpoint=LLMConfig.AZURE_ENDPOINT,
            api_key=LLMConfig.AZURE_API_KEY,
            temperature=0,
            max_tokens=4000,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLMConfig.OPENAI_MODEL,
            api_key=LLMConfig.OPENAI_API_KEY,
            temperature=0,
            max_tokens=4000,
        )
    else:
        raise ValueError(f"Provider non supportato: {provider}")


EXTRACTION_SYSTEM_PROMPT = """Sei un esperto di test automation che analizza documenti di test case.

Il tuo compito è identificare e strutturare gli scenari di test contenuti nel documento.

Per ogni scenario devi estrarre:
1. **id**: un identificatore univoco (es. "scenario_1", "scenario_2")
2. **name**: nome descrittivo dello scenario
3. **execution_steps**: lista di passi da eseguire (frasi concise, imperative)
4. **expected_results**: lista di risultati attesi (cosa deve succedere)

REGOLE:
- Se il documento contiene scenari numerati (primo, secondo, terzo, quarto), crea uno scenario separato per ognuno
- Se il documento descrive un unico flusso, crea un solo scenario
- Gli execution_steps devono essere azioni concrete e sequenziali
- Gli expected_results devono essere verificabili
- Usa id sequenziali: scenario_1, scenario_2, ecc.

FORMATO OUTPUT:
Rispondi SOLO con un JSON array valido (no markdown, no spiegazioni):

[
  {
    "id": "scenario_1",
    "name": "Nome descrittivo",
    "execution_steps": [
      "Passo 1",
      "Passo 2"
    ],
    "expected_results": [
      "Risultato atteso 1",
      "Risultato atteso 2"
    ]
  },
  ...
]"""


def extract_scenarios_with_llm(
    title: str,
    initial_conditions: str,
    test_steps: str,
    expected_results: str
) -> List[LabScenario]:
    """
    Usa LLM per estrarre scenari strutturati da testo libero.
    
    Args:
        title: Titolo del caso di test
        initial_conditions: Prerequisiti
        test_steps: Passi di esecuzione (può contenere più scenari)
        expected_results: Risultati attesi (può contenere più scenari)
    
    Returns:
        Lista di LabScenario oggetti
    """
    
    # Costruisci il prompt utente
    user_prompt = f"""Documento di Test Case:

TITOLO: {title}

CONDIZIONI INIZIALI (prerequisiti):
{initial_conditions}

PASSI DEL TEST:
{test_steps}

RISULTATI ATTESI:
{expected_results}

---

Estrai gli scenari di test da questo documento e restituiscili come JSON array."""
    
    # Chiama LLM
    llm = get_llm_for_extraction()
    
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    response_text = response.content
    
    # Pulisci la risposta (rimuovi markdown code blocks se presenti)
    response_text = response_text.strip()
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'^```\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    
    # Parse JSON
    try:
        scenarios_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM ha restituito JSON non valido: {e}\n\nRisposta:\n{response_text}")
    
    # Converti in LabScenario objects
    scenarios = []
    for data in scenarios_data:
        scenario = LabScenario(
            id=data.get('id', f"scenario_{len(scenarios) + 1}"),
            name=data.get('name', 'Unnamed scenario'),
            execution_steps=data.get('execution_steps', []),
            expected_results=data.get('expected_results', []),
            prompt_hints=None  # Opzionale, può essere aggiunto manualmente dopo
        )
        scenarios.append(scenario)
    
    return scenarios


def extract_scenarios_from_document(parsed_doc: Dict[str, str]) -> List[LabScenario]:
    """
    Estrae scenari da un documento già parsato.
    
    Args:
        parsed_doc: Output di document_parser.parse()
    
    Returns:
        Lista di LabScenario
    """
    return extract_scenarios_with_llm(
        title=parsed_doc.get('title', 'Untitled'),
        initial_conditions=parsed_doc.get('initial_conditions', ''),
        test_steps=parsed_doc.get('test_steps', ''),
        expected_results=parsed_doc.get('expected_results', '')
    )


def scenarios_to_dict(scenarios: List[LabScenario]) -> List[Dict]:
    """Converte lista di LabScenario in lista di dict (per JSON serialization)."""
    return [
        {
            'id': s.id,
            'name': s.name,
            'execution_steps': s.execution_steps,
            'expected_results': s.expected_results,
            'prompt_hints': s.prompt_hints
        }
        for s in scenarios
    ]


def scenarios_to_python_code(scenarios: List[LabScenario]) -> str:
    """
    Genera codice Python per aggiungere gli scenari a lab_scenarios.py.
    
    Utile per review manuale prima di committare.
    """
    lines = []
    lines.append("# Scenari estratti automaticamente\n")
    
    for s in scenarios:
        lines.append(f"LabScenario(")
        lines.append(f"    id=\"{s.id}\",")
        lines.append(f"    name=\"{s.name}\",")
        lines.append(f"    expected_results=[")
        for result in s.expected_results:
            # Escape quotes
            result_escaped = result.replace('"', '\\"')
            lines.append(f"        \"{result_escaped}\",")
        lines.append(f"    ],")
        lines.append(f"    execution_steps=[")
        for step in s.execution_steps:
            step_escaped = step.replace('"', '\\"')
            lines.append(f"        \"{step_escaped}\",")
        lines.append(f"    ],")
        lines.append(f"    prompt_hints=None,")
        lines.append(f"),\n")
    
    return "\n".join(lines)


# === CLI per testing ===
if __name__ == "__main__":
    import sys
    from agent.document_parser import parse_test_document
    
    if len(sys.argv) < 2:
        print("Uso: python scenario_extractor.py <file_path>")
        print("\nEstrae scenari da un documento di test usando LLM")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # 1. Parse documento
        print(f"📄 Parsing documento: {file_path}")
        parsed = parse_test_document(file_path)
        print(f"✓ Titolo: {parsed['title']}\n")
        
        # 2. Estrai scenari con LLM
        print("🤖 Estrazione scenari con LLM...")
        scenarios = extract_scenarios_from_document(parsed)
        print(f"✓ Estratti {len(scenarios)} scenari\n")
        
        # 3. Mostra risultati
        print("=" * 60)
        print("SCENARI ESTRATTI (JSON)")
        print("=" * 60)
        print(json.dumps(scenarios_to_dict(scenarios), indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 60)
        print("CODICE PYTHON (per lab_scenarios.py)")
        print("=" * 60)
        print(scenarios_to_python_code(scenarios))
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
