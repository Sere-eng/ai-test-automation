"""
Scenario Extractor - Converte documenti di test in scenari strutturati usando LLM.

Il LLM viene usato SOLO per:
- Ricomporre frasi frammentate (problema strutturale dei docx Word)
- Identificare i confini tra scenari multipli
- Strutturare l'output in JSON

Il LLM NON deve riscrivere, parafrasare o sintetizzare il testo originale.
Vedi EXTRACTION_SYSTEM_PROMPT per le regole di fedeltà al testo.
"""

from __future__ import annotations

import json
import re
from typing import List, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from agent.lab_scenarios import LabScenario
from agent.prompts.extraction import EXTRACTION_SYSTEM_PROMPT
from agent.setup import create_llm


def extract_scenarios_with_llm(
    title: str, initial_conditions: str, test_steps: str, expected_results: str
) -> List[LabScenario]:
    user_prompt = f"""Documento di Test Case:

TITOLO: {title}

CONDIZIONI INIZIALI (prerequisiti):
{initial_conditions}

PASSI DEL TEST:
{test_steps}

RISULTATI ATTESI:
{expected_results}

---

Estrai gli scenari di test da questo documento.
Ricorda: copia il testo VERBATIM, ricomponi solo i frammenti spezzati dalla
formattazione Word, non riscrivere nulla."""

    llm = create_llm(temperature=0, max_tokens=4000)

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    response_text = response.content

    response_text = response_text.strip()
    response_text = re.sub(r"^```json\s*", "", response_text)
    response_text = re.sub(r"^```\s*", "", response_text)
    response_text = re.sub(r"\s*```$", "", response_text)

    try:
        scenarios_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM ha restituito JSON non valido: {e}\n\nRisposta:\n{response_text}"
        )

    scenarios: List[LabScenario] = []
    for data in scenarios_data:
        scenario = LabScenario(
            id=data.get("id", f"scenario_{len(scenarios) + 1}"),
            name=data.get("name", "Unnamed scenario"),
            execution_steps=data.get("execution_steps", []),
            expected_results=data.get("expected_results", []),
            prompt_hints=None,
        )
        scenarios.append(scenario)

    return scenarios


def extract_scenarios_from_document(parsed_doc: Dict[str, str]) -> List[LabScenario]:
    return extract_scenarios_with_llm(
        title=parsed_doc.get("title", "Untitled"),
        initial_conditions=parsed_doc.get("initial_conditions", ""),
        test_steps=parsed_doc.get("test_steps", ""),
        expected_results=parsed_doc.get("expected_results", ""),
    )


def scenarios_to_dict(scenarios: List[LabScenario]) -> List[Dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "execution_steps": s.execution_steps,
            "expected_results": s.expected_results,
            "prompt_hints": s.prompt_hints,
        }
        for s in scenarios
    ]


def scenarios_to_python_code(scenarios: List[LabScenario]) -> str:
    lines = []
    lines.append("# Scenari estratti automaticamente\n")

    for s in scenarios:
        lines.append("LabScenario(")
        lines.append(f'    id="{s.id}",')
        lines.append(f'    name="{s.name}",')
        lines.append("    expected_results=[")
        for result in s.expected_results:
            result_escaped = result.replace('"', '\\"')
            lines.append(f'        "{result_escaped}",')
        lines.append("    ],")
        lines.append("    execution_steps=[")
        for step in s.execution_steps:
            step_escaped = step.replace('"', '\\"')
            lines.append(f'        "{step_escaped}",')
        lines.append("    ],")
        lines.append("    prompt_hints=None,")
        lines.append("),\n")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from agent.extraction.document_parser import parse_test_document

    if len(sys.argv) < 2:
        print("Uso: python scenario_extractor.py <file_path>")
        print("\nEstrae scenari da un documento di test usando LLM (testo verbatim)")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        print(f"📄 Parsing documento: {file_path}")
        parsed = parse_test_document(file_path)
        print(f"✓ Titolo: {parsed['title']}\n")

        print("🤖 Estrazione scenari con LLM (verbatim)...")
        scenarios = extract_scenarios_from_document(parsed)
        print(f"✓ Estratti {len(scenarios)} scenari\n")

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

