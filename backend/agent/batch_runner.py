# backend/agent/batch_runner.py
"""
Batch Test Runner - Esegue più scenari LAB in sequenza.
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json

from agent.lab_scenarios import LabScenario
from agent.orchestrator import run_prefix_to_home, run_lab_scenario
from agent.utils import make_json_serializable


class BatchTestRunner:
    """Esegue batch di scenari LAB."""
    
    def __init__(self, 
                 url: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None):
        """
        Args:
            url: URL dell'applicazione (None = usa config)
            username: Username per login (None = usa config)
            password: Password per login (None = usa config)
        """
        self.url = url
        self.username = username
        self.password = password
        self.results = []
        
    async def run_single_scenario(self, scenario: LabScenario, verbose: bool = True) -> Dict:
        """
        Esegue un singolo scenario completo (prefix + scenario).
        
        Args:
            scenario: LabScenario da eseguire
            verbose: Se True stampa log durante esecuzione
        
        Returns:
            Dict con risultato del test
        """
        scenario_result = {
            'scenario_id': scenario.id,
            'scenario_name': scenario.name,
            'started_at': datetime.now().isoformat(),
            'prefix_result': None,
            'scenario_result': None,
            'overall_status': 'unknown',
            'error': None
        }
        
        try:
            if verbose:
                print(f"\n{'=' * 60}")
                print(f"🚀 Scenario: {scenario.name} ({scenario.id})")
                print(f"{'=' * 60}\n")
            
            # Fase 1: Prefix (login → home)
            if verbose:
                print("📋 Fase 1: Login e navigazione modulo LAB...")
            
            prefix_result = await run_prefix_to_home(
                verbose=verbose,
                url=self.url,
                user=self.username,
                password=self.password
            )
            scenario_result['prefix_result'] = make_json_serializable(prefix_result)
            
            if prefix_result.get('status') != 'success':
                scenario_result['overall_status'] = 'failed'
                scenario_result['error'] = f"Prefix failed: {prefix_result.get('error', 'unknown')}"
                if verbose:
                    print(f"❌ Prefix fallito: {scenario_result['error']}")
                return scenario_result
            
            if verbose:
                print("✓ Prefix completato\n")
                print("📋 Fase 2: Esecuzione scenario...")
            
            # Fase 2: Scenario specifico (passa l'oggetto scenario diretto)
            scenario_exec_result = await run_lab_scenario(scenario=scenario, verbose=verbose)
            scenario_result['scenario_result'] = make_json_serializable(scenario_exec_result)
            
            # Determina status finale
            if scenario_exec_result.get('status') == 'success':
                scenario_result['overall_status'] = 'success'
                if verbose:
                    print(f"\n✅ Scenario {scenario.id} COMPLETATO CON SUCCESSO")
            else:
                scenario_result['overall_status'] = 'failed'
                scenario_result['error'] = scenario_exec_result.get('error', 'unknown')
                if verbose:
                    print(f"\n❌ Scenario {scenario.id} FALLITO: {scenario_result['error']}")
        
        except Exception as e:
            scenario_result['overall_status'] = 'error'
            scenario_result['error'] = str(e)
            if verbose:
                print(f"\n💥 ERRORE: {e}")
        
        finally:
            scenario_result['completed_at'] = datetime.now().isoformat()
        
        return scenario_result
    
    async def run_batch(self, scenarios: List[LabScenario], verbose: bool = True) -> Dict:
        """
        Esegue una batch di scenari in sequenza.
        
        Args:
            scenarios: Lista di LabScenario da eseguire
            verbose: Se True stampa log durante esecuzione
        
        Returns:
            Dict con risultati aggregati di tutti gli scenari
        """
        batch_result = {
            'started_at': datetime.now().isoformat(),
            'total_scenarios': len(scenarios),
            'scenarios': [],
            'summary': {
                'success': 0,
                'failed': 0,
                'error': 0
            }
        }
        
        if verbose:
            print(f"\n🔄 Avvio batch test: {len(scenarios)} scenari")
            print(f"{'=' * 80}\n")
        
        for idx, scenario in enumerate(scenarios, 1):
            if verbose:
                print(f"\n📊 Scenario {idx}/{len(scenarios)}")
            
            result = await self.run_single_scenario(scenario, verbose=verbose)
            batch_result['scenarios'].append(result)
            
            # Aggiorna summary
            status = result['overall_status']
            if status in batch_result['summary']:
                batch_result['summary'][status] += 1
            
            if verbose:
                print(f"\n{'─' * 80}")
        
        batch_result['completed_at'] = datetime.now().isoformat()
        
        # Stampa summary finale
        if verbose:
            print(f"\n{'=' * 80}")
            print("📈 RIEPILOGO BATCH TEST")
            print(f"{'=' * 80}")
            print(f"Totale scenari: {batch_result['total_scenarios']}")
            print(f"✅ Successo: {batch_result['summary']['success']}")
            print(f"❌ Falliti: {batch_result['summary']['failed']}")
            print(f"💥 Errori: {batch_result['summary']['error']}")
            print(f"{'=' * 80}\n")
        
        return batch_result
    
    def save_results(self, results: Dict, output_dir: str = "data/results"):
        """
        Salva i risultati del batch in un file JSON.
        
        Args:
            results: Dict con risultati (da run_batch)
            output_dir: Directory dove salvare i risultati
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_test_{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return str(filepath)


# Funzioni di convenienza per uso sincrono
def run_batch_sync(
    scenarios: List[LabScenario],
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    verbose: bool = True,
    save_results: bool = True
) -> Dict:
    """
    Esegue batch di scenari (versione sincrona per Flask).
    
    Args:
        scenarios: Lista di LabScenario da eseguire
        url: URL dell'applicazione (None = usa config)
        username: Username (None = usa config)
        password: Password (None = usa config)
        verbose: Se True stampa log
        save_results: Se True salva risultati su file
    
    Returns:
        Dict con risultati del batch
    """
    runner = BatchTestRunner(url=url, username=username, password=password)
    
    # Esegui in asyncio event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    results = loop.run_until_complete(runner.run_batch(scenarios, verbose=verbose))
    
    if save_results:
        filepath = runner.save_results(results)
        results['saved_to'] = filepath
        if verbose:
            print(f"💾 Risultati salvati in: {filepath}")
    
    return results


# === CLI per testing ===
if __name__ == "__main__":
    import sys
    from agent.lab_scenarios import LAB_SCENARIOS
    
    if len(sys.argv) < 2:
        print("Uso: python batch_runner.py <scenario_ids>")
        print("\nEsempi:")
        print("  python batch_runner.py scenario_1")
        print("  python batch_runner.py scenario_1 scenario_2 scenario_3")
        print("  python batch_runner.py all  # esegue tutti gli scenari")
        print(f"\nScenari disponibili: {', '.join([s.id for s in LAB_SCENARIOS])}")
        sys.exit(1)
    
    scenario_ids = sys.argv[1:]
    
    # Se primo arg è "all", esegui tutti
    if scenario_ids[0] == "all":
        scenarios_to_run = LAB_SCENARIOS
    else:
        # Filtra scenari richiesti
        scenarios_to_run = [s for s in LAB_SCENARIOS if s.id in scenario_ids]
        
        if not scenarios_to_run:
            print(f"❌ Nessuno scenario trovato con ID: {scenario_ids}")
            print(f"Scenari disponibili: {', '.join([s.id for s in LAB_SCENARIOS])}")
            sys.exit(1)
    
    # Esegui batch
    try:
        results = run_batch_sync(scenarios_to_run, verbose=True, save_results=True)
        
        # Exit code in base ai risultati
        if results['summary']['failed'] > 0 or results['summary']['error'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        print(f"\n💥 ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
