# backend/agent/lab_scenarios.py
"""
Definizione degli scenari LAB dopo login e selezione organizzazione.
Usato da: workflow runner, prompt di riferimento, mapping test in linguaggio naturale.
Prefix fisso: login → Seleziona organizzazione → Continua → home.
Da qui in poi si applica uno (o più) degli scenari sotto.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LabScenario:
    """Uno scenario eseguibile sulla piattaforma LAB dopo il prefix fisso."""
    id: str
    name: str
    expected_results: List[str]
    execution_steps: List[str]
    prompt_hints: Optional[str] = None  # istruzioni operative specifiche per l'agente


LAB_SCENARIOS: List[LabScenario] = [
    LabScenario(
        id="scenario_1",
        name="Creazione filtro e visualizzazione in dashboard",
        expected_results=[
            "Nella dashboard il filtro realizzato viene correttamente memorizzato "
            "e visualizzato in una card con il nome del filtro.",
            "La card contiene i campioni che rispettano le logiche inserite nel filtro "
            "(es. appartenenza a uno o più piani di lavoro, range temporale).",
        ],
        execution_steps=[
            "Dal menu laterale clicca direttamente sulla voce 'Laboratorio'.",
            "Accedere alla dashboard di interesse selezionandola dal dropdown menu "
            "(se è presente solo una dashboard è valorizzata di default).",
            "Accedere alla funzionalità 'Modifica'.",
            "Creare un nuovo elemento cliccando 'Aggiungi Gruppo'.",
            "Compilare il campo obbligatorio del gruppo e successivamente creare un nuovo filtro.",
            "Compilare il campo obbligatorio del filtro e salvare.",
        ],
        prompt_hints=None,
    ),
    LabScenario(
        id="scenario_2",
        name="Accesso tramite contatori in dashboard",
        expected_results=[
            "Accedendo tramite un contatore posto in alto nella dashboard si viene reindirizzati alla pagina di elenco campioni.",
            "I campioni elencati appartengono allo stato indicato nel nome del contatore (es. contatore 'Campioni con Check-in' → solo campioni in stato di check-in).",
            "Il numero totale di righe visualizzate in fondo alla lista corrisponde al valore del contatore cliccato.",
            "In caso di contatore a 0, la card corrispondente non è cliccabile.",
        ],
        execution_steps=[
            "Dal menu laterale clicca sulla voce 'Laboratorio'; se il menu a tendina delle dashboard contiene più voci seleziona quella desiderata (altrimenti usa quella già preselezionata) e attendi che venga visualizzata la dashboard con i contatori in alto.",
            "Nella dashboard del Laboratorio individua i contatori mostrati in alto e scegli un contatore con numero diverso da 0 (ad esempio 'Campioni con Check-in').",
            "Clicca sul contatore selezionato e attendi che venga aperta la pagina di elenco campioni.",
            "Verifica che la pagina mostri il titolo 'Attività di dettaglio dashboard' e leggi il contatore 'Totale righe visualizzate' visualizzato in fondo alla lista.",
        ],
        prompt_hints=None,
        ),
    LabScenario(
        id="scenario_3",
        name="Accesso tramite filtro",
        expected_results=[
            "Viene aperta la pagina 'Attività di dettaglio dashboard' con il filtro selezionato indicato nel dropdown in alto.",
            "Vengono mostrati i campioni del filtro; il footer indica il totale (es. 'Totale righe visualizzate : X su Y').",
            "Con più di 50 campioni vengono caricati 50 per volta; scorrendo la lista si caricano i successivi.",
            "Se il filtro contiene un solo campione, si viene reindirizzati direttamente alla pagina di dettaglio.",
        ],
        execution_steps=[
            "Dalla dashboard del Laboratorio individua la sezione 'Filtri' con i gruppi e i relativi filtri.",
            "Scegli un filtro con numero maggiore di 0 e cliccaci sopra.",
            "Attendi che venga aperta la pagina 'Attività di dettaglio dashboard' con il nome del filtro visibile nel dropdown in alto.",
            "Leggi il contatore totale visualizzato in fondo alla lista (es. 'Totale righe visualizzate').",
        ],
        prompt_hints=None,
    ),
    LabScenario(
        id="scenario_4",
        name="Pagina di dettaglio campione",
        expected_results=[
            "Viene visualizzata la pagina di dettaglio del campione nel quale si è entrati.",
        ],
        execution_steps=[
            "Dal menu laterale clicca sulla voce 'Laboratorio'; se il menu a tendina delle dashboard contiene più voci seleziona quella desiderata (altrimenti usa quella già preselezionata) e attendi che venga visualizzata la dashboard con i contatori in alto.",
            "Dalla dashboard del Laboratorio clicca su un contatore con numero diverso da 0 (es. 'Campioni con Check-in').",
            "Attendi che venga aperta la pagina 'Attività di dettaglio dashboard' con l'elenco campioni.",
            "Clicca su una riga qualsiasi dell'elenco.",
            "Attendi che venga aperta la pagina 'Attività di dettaglio del campione di laboratorio'.",
        ],
        prompt_hints=None,
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