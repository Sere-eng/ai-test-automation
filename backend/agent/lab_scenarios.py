# backend/agent/lab_scenarios.py
"""
Definizione degli scenari LAB dopo login e selezione organizzazione.
Usato da: workflow runner, prompt di riferimento, mapping test in linguaggio naturale.
Prefix fisso: login → Seleziona organizzazione → Continua → home.
Da qui in poi si applica uno (o più) degli scenari sotto.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class LabScenario:
    """Uno scenario eseguibile sulla piattaforma LAB dopo il prefix fisso."""
    id: str
    name: str
    expected_results: List[str]
    execution_steps: List[str]


LAB_SCENARIOS: List[LabScenario] = [
    LabScenario(
        id="scenario_1",
        name="Creazione filtro e visualizzazione in dashboard",
        expected_results=[
            "Nella dashboard il filtro realizzato viene correttamente memorizzato e visualizzato in una card.",
            "La card contiene i campioni che rispettano le logiche inserite nel filtro "
            "(es. appartenenza a uno o più piani di lavoro, range temporale).",
        ],
        execution_steps=[
            "Dal modulo Laboratory (dove compare ad es. Preanalitica), apri la sezione 'Laboratorio' dal menu laterale: clicca la voce di menu con etichetta 'Laboratorio' (icona science). La dashboard Laboratorio si apre con dropdown già valorizzato se c'è una sola dashboard.",
            "Nella tab 'Filtri' della dashboard Laboratorio, clicca il pulsante 'Modifica'.",
            "Crea un nuovo gruppo: clicca 'Aggiungi gruppo'. Appare una nuova card con un campo di testo nell'header (senza label, può essere precompilato con 'title'): inserisci lì il titolo del gruppo (obbligatorio). Poi clicca 'Aggiungi filtro' dentro quella card.",
            "Nella modale: compila almeno il campo obbligatorio 'Nome filtro' (label 'Nome filtro*'); poi clicca 'Conferma' per salvare il filtro.",
        ],
    ),
    LabScenario(
        id="scenario_2",
        name="Accesso tramite contatori in dashboard",
        expected_results=[
            "Accedendo tramite contatori posti in alto nella dashboard si viene reindirizzati alla pagina di elenco campioni.",
            "I campioni hanno lo stesso stato indicato nel nome del contatore "
            "(es. contatore 'checkin' → solo campioni in stato checkin, in numero pari a quello indicato nel contatore).",
            "In caso di contatore a 0, la card non è cliccabile.",
        ],
        execution_steps=[
            "Accedere alla dashboard.",
            "Accedere al contatore mostrato in alto nella dashboard (con un numero diverso da 0).",
        ],
    ),
    LabScenario(
        id="scenario_3",
        name="Accesso tramite filtro",
        expected_results=[
            "Vengono mostrati solo i campioni contenuti nel filtro, in numero pari a quelli indicati nel filtro.",
            "Il numero è indicato in fondo alla tabella; con molti campioni vengono caricati 50 per volta (scroll) fino al totale.",
            "Se il filtro contiene un solo elemento, si viene indirizzati direttamente alla pagina di dettaglio del campione.",
        ],
        execution_steps=[
            "Accedere alla dashboard.",
            "Accedere al filtro presente in un gruppo.",
        ],
    ),
    LabScenario(
        id="scenario_4",
        name="Pagina di dettaglio campione",
        expected_results=[
            "Viene visualizzata la pagina di dettaglio del campione nel quale si è entrati.",
        ],
        execution_steps=[
            "Accedere a un campione cliccando su una riga in elenco campioni.",
        ],
    ),
]


def get_scenario_by_id(scenario_id: str) -> LabScenario | None:
    """Restituisce lo scenario con l'id dato, o None."""
    for s in LAB_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def format_scenarios_for_prompt() -> str:
    """
    Restituisce una stringa con scenari formattati per inclusion nel system prompt
    o per contesto all'agente (solo passi di esecuzione + risultati attesi).
    """
    lines = [
        "Scenari LAB (dopo login e selezione organizzazione).",
        "Prefix fisso: login → Seleziona organizzazione → Continua → home.",
        "",
    ]
    for s in LAB_SCENARIOS:
        lines.append(f"Scenario: {s.name} (id: {s.id})")
        lines.append("  Passi di esecuzione:")
        for step in s.execution_steps:
            lines.append(f"    - {step}")
        lines.append("  Risultati attesi:")
        for res in s.expected_results:
            lines.append(f"    - {res}")
        lines.append("")
    return "\n".join(lines)
