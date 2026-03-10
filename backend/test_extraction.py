# backend/test_extraction.py
"""
Script di test per l'estrazione automatica degli scenari da documenti JIRA.
Mostra:
1. Parsing del documento (estrazione testo grezzo)
2. Estrazione scenari con LLM Azure OpenAI
3. Formato output per il sistema di test automation
"""

import sys
import json
from pathlib import Path

# Aggiungi backend al path
sys.path.insert(0, str(Path(__file__).parent))

from agent.document_parser import TestDocumentParser, parse_test_document
from agent.scenario_extractor import extract_scenarios_from_document, scenarios_to_dict
from config.settings import LLMConfig


def print_section(title: str, width: int = 80):
    """Stampa una sezione separata."""
    print(f"\n{'=' * width}")
    print(f"{title.center(width)}")
    print(f"{'=' * width}\n")


def test_document_extraction(doc_path: str):
    """
    Testa l'estrazione completa di un documento.
    
    Args:
        doc_path: Percorso al documento JIRA (.doc/.html)
    """
    
    # Verifica LLM provider
    provider = LLMConfig.get_provider()
    print_section("CONFIGURAZIONE LLM")
    print(f"Provider: {provider.upper()}")
    
    if provider == "azure":
        print(f"Endpoint: {LLMConfig.AZURE_ENDPOINT}")
        print(f"Deployment: {LLMConfig.AZURE_DEPLOYMENT}")
        print(f"API Version: {LLMConfig.AZURE_API_VERSION}")
    elif provider == "openrouter":
        print(f"Model: {LLMConfig.OPENROUTER_MODEL}")
    elif provider == "openai":
        print(f"Model: {LLMConfig.OPENAI_MODEL}")
    
    # STEP 1: Parse del documento
    print_section("STEP 1: PARSING DOCUMENTO")
    print(f"📄 File: {doc_path}\n")
    
    try:
        parser = TestDocumentParser(doc_path)
        parsed = parser.parse()
        
        print(f"✅ Parsing completato!")
        print(f"\n📋 Titolo: {parsed['title']}")
        print(f"📝 Formato: {parsed.get('format', 'unknown')}")
        
        print(f"\n📌 PREREQUISITI:")
        print("-" * 80)
        prerequisites = parsed.get('initial_conditions', 'N/A')
        print(prerequisites[:300] + "..." if len(prerequisites) > 300 else prerequisites)
        
        print(f"\n📝 PASSI DEL TEST:")
        print("-" * 80)
        test_steps = parsed.get('test_steps', 'N/A')
        print(test_steps[:500] + "..." if len(test_steps) > 500 else test_steps)
        
        print(f"\n✅ RISULTATI ATTESI:")
        print("-" * 80)
        expected = parsed.get('expected_results', 'N/A')
        print(expected[:500] + "..." if len(expected) > 500 else expected)
        
    except Exception as e:
        print(f"❌ Errore nel parsing: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # STEP 2: Estrazione scenari con LLM
    print_section("STEP 2: ESTRAZIONE SCENARI CON LLM")
    print("🤖 Chiamata a Azure OpenAI per estrarre scenari strutturati...\n")
    
    try:
        scenarios = extract_scenarios_from_document(parsed)
        
        print(f"✅ Estratti {len(scenarios)} scenari!\n")
        
        # Mostra dettagli per ogni scenario
        for i, scenario in enumerate(scenarios, 1):
            print(f"{'─' * 80}")
            print(f"📋 SCENARIO {i}: {scenario.name}")
            print(f"   ID: {scenario.id}")
            print(f"{'─' * 80}")
            
            print(f"\n🔹 EXECUTION STEPS ({len(scenario.execution_steps)} passi):")
            for j, step in enumerate(scenario.execution_steps, 1):
                print(f"   {j}. {step}")
            
            print(f"\n🔹 EXPECTED RESULTS ({len(scenario.expected_results)} risultati):")
            for j, result in enumerate(scenario.expected_results, 1):
                print(f"   {j}. {result}")
            
            print()
        
    except Exception as e:
        print(f"❌ Errore nell'estrazione LLM: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # STEP 3: Formato per sistema automation
    print_section("STEP 3: FORMATO PER SISTEMA AUTOMATION")
    
    scenarios_dict = scenarios_to_dict(scenarios)
    
    print("📦 JSON per API /api/test/batch:\n")
    print(json.dumps({
        "scenarios": scenarios_dict,
        "url": "https://your-lab-url.com",
        "username": "your-username",
        "password": "your-password"
    }, indent=2, ensure_ascii=False))
    
    # STEP 4: Salva output
    print_section("STEP 4: SALVATAGGIO OUTPUT")
    
    output_dir = Path("data/test-cases")
    output_file = output_dir / f"{Path(doc_path).stem}_scenarios.json"
    
    output_data = {
        "source_document": str(Path(doc_path).name),
        "extracted_at": __import__('datetime').datetime.now().isoformat(),
        "llm_provider": provider,
        "title": parsed['title'],
        "prerequisites": parsed.get('initial_conditions', ''),
        "scenarios_count": len(scenarios),
        "scenarios": scenarios_dict
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Scenarios salvati in: {output_file}")
    
    # STEP 5: Codice Python per lab_scenarios.py
    print_section("STEP 5: CODICE PYTHON (opzionale)")
    print("📝 Copia questo codice in backend/agent/lab_scenarios.py:\n")
    print("# Scenari estratti automaticamente da", Path(doc_path).name)
    
    from agent.scenario_extractor import scenarios_to_python_code
    print(scenarios_to_python_code(scenarios))
    
    return scenarios


if __name__ == "__main__":
    # Default: usa il documento in data/test-cases
    doc_path = "data/test-cases/HC40DIAGOL-7155.doc"
    
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
    
    if not Path(doc_path).exists():
        print(f"❌ File non trovato: {doc_path}")
        print(f"\nUso corretto:")
        print(f"  python test_extraction.py [path_to_document]")
        print(f"\nEsempio:")
        print(f"  python test_extraction.py data/test-cases/HC40DIAGOL-7155.doc")
        sys.exit(1)
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║              TEST ESTRAZIONE SCENARI DA DOCUMENTO JIRA                        ║
║                                                                               ║
║  Questo script mostra come i documenti JIRA vengono trasformati              ║
║  in scenari strutturati per il sistema di test automation                    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    scenarios = test_document_extraction(doc_path)
    
    if scenarios:
        print_section("✅ TEST COMPLETATO CON SUCCESSO")
        print(f"📊 Totale scenari estratti: {len(scenarios)}")
        print("\n🚀 Prossimi passi:")
        print("   1. Verifica che gli scenari estratti siano corretti")
        print("   2. Usa POST /api/test/batch per eseguire i test")
        print("   3. Oppure aggiungi manualmente gli scenari a lab_scenarios.py")
    else:
        print_section("❌ TEST FALLITO")
        print("Controlla gli errori sopra")
