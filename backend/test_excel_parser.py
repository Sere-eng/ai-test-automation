#!/usr/bin/env python3
"""
Test script per verificare il parsing di file Excel/CSV.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.document_parser import parse_test_document


def test_csv_parsing():
    """Test parsing del file CSV con casi di test."""
    
    # Path al file CSV
    csv_file = Path(__file__).parent.parent / "Casi di test di CPOE-T validi il 03.03.2026 (1).csv"
    
    if not csv_file.exists():
        print(f"❌ File non trovato: {csv_file}")
        return False
    
    print(f"📄 Testing file: {csv_file.name}")
    print(f"   Path: {csv_file}")
    print()
    
    try:
        # Parse il documento
        result = parse_test_document(str(csv_file))
        
        print("✅ Parsing completato con successo!")
        print()
        print("=" * 70)
        print("RISULTATI DEL PARSING")
        print("=" * 70)
        print()
        
        # Informazioni generali
        print(f"Titolo:        {result.get('title')}")
        print(f"Formato:       {result.get('format')}")
        print(f"Casi di test:  {result.get('test_cases_count')}")
        print()
        
        # Colonne trovate
        columns = result.get('columns_found', {})
        print("Colonne identificate:")
        for field, col_name in columns.items():
            status = "✓" if col_name else "✗"
            print(f"  {status} {field:20s} → {col_name or '(non trovata)'}")
        print()
        
        # Primi 3 casi di test come esempio
        test_cases = result.get('test_cases', [])
        if test_cases:
            print("=" * 70)
            print("PRIMI 3 CASI DI TEST (ESEMPI)")
            print("=" * 70)
            
            for i, test_case in enumerate(test_cases[:3], 1):
                print()
                print(f"--- Test Case #{i} (Riga {test_case.get('row_number')}) ---")
                print()
                
                if test_case.get('objective'):
                    print(f"OBIETTIVO:")
                    print(f"  {test_case['objective'][:200]}...")
                    print()
                
                if test_case.get('prerequisites'):
                    print(f"PREREQUISITI:")
                    prereq_lines = test_case['prerequisites'].split('\n')
                    for line in prereq_lines[:5]:  # Prime 5 righe
                        if line.strip():
                            print(f"  {line}")
                    if len(prereq_lines) > 5:
                        print(f"  ... (+ {len(prereq_lines) - 5} righe)")
                    print()
                
                if test_case.get('description'):
                    print(f"DESCRIZIONE:")
                    desc_lines = test_case['description'].split('\n')
                    for line in desc_lines[:5]:
                        if line.strip():
                            print(f"  {line}")
                    if len(desc_lines) > 5:
                        print(f"  ... (+ {len(desc_lines) - 5} righe)")
                    print()
                
                if test_case.get('expected_results'):
                    print(f"RISULTATI ATTESI:")
                    exp_lines = test_case['expected_results'].split('\n')
                    for line in exp_lines[:5]:
                        if line.strip():
                            print(f"  {line}")
                    if len(exp_lines) > 5:
                        print(f"  ... (+ {len(exp_lines) - 5} righe)")
        
        print()
        print("=" * 70)
        print(f"✅ Totale casi di test estratti: {len(test_cases)}")
        print("=" * 70)
        
        # Salva risultati in JSON per ispezione
        output_file = Path(__file__).parent / "data" / "test-cases" / f"{csv_file.stem}_parsed.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print()
        print(f"📝 Risultati completi salvati in: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il parsing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_structure():
    """Test della struttura dei dati estratti."""
    
    csv_file = Path(__file__).parent.parent / "Casi di test di CPOE-T validi il 03.03.2026 (1).csv"
    
    if not csv_file.exists():
        return False
    
    try:
        result = parse_test_document(str(csv_file))
        
        # Verifica che abbia la struttura corretta
        assert 'title' in result, "Manca 'title'"
        assert 'format' in result, "Manca 'format'"
        assert 'test_cases' in result, "Manca 'test_cases'"
        assert 'test_cases_count' in result, "Manca 'test_cases_count'"
        assert 'columns_found' in result, "Manca 'columns_found'"
        
        # Verifica i campi di ogni test case
        test_cases = result.get('test_cases', [])
        if test_cases:
            first_case = test_cases[0]
            required_fields = ['row_number', 'objective', 'prerequisites', 'description', 'expected_results']
            for field in required_fields:
                assert field in first_case, f"Manca il campo '{field}' nel test case"
        
        print("\n✅ Struttura dati verificata correttamente!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Errore nella struttura: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("TEST PARSER EXCEL/CSV")
    print("=" * 70)
    print()
    
    # Test 1: Parsing base
    success1 = test_csv_parsing()
    
    # Test 2: Verifica struttura
    if success1:
        print()
        success2 = test_excel_structure()
    else:
        success2 = False
    
    # Risultato finale
    print()
    print("=" * 70)
    if success1 and success2:
        print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO!")
    else:
        print("❌ ALCUNI TEST SONO FALLITI")
    print("=" * 70)
    
    sys.exit(0 if (success1 and success2) else 1)
