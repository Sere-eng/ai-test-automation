# backend/codegen/trace_to_playwright.py
"""
Regole deterministiche per compilare una trace MCP in uno script Playwright Python.

Non usa LLM: ogni tool viene tradotto secondo una mappa fissa → codice Python.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Nomi di icone Material che appaiono come testo accessibile ma non sono
# interazioni utente reali (es. click su "menu", "science", "add").
# Se tutti i targets di un click_smart puntano a uno di questi testi, lo step
# viene omesso dallo script generato.
_MATERIAL_ICON_NAMES = {
    "menu",
    "science",
    "mic",
    "refresh",
    "add",
    "more_vert",
    "edit",
    "delete",
    "chevron_left",
    "chevron_right",
    "search",
    "settings",
    "person",
    "notifications",
    "home",
    "tune",
    "share",
    "fast_forward",
    "track_changes",
    "assignment",
    "widgets",
    "face",
    "unarchive",
    "design_services",
    "android",
    "query_stats",
    "medical_services",
    "vpn_key",
    "email",
    "list",
    "developer_board",
    "person_pin",
    "multiline_chart",
    "contact_phone",
}


def generate_script_from_trace(
    trace: List[Dict[str, Any]],
    scenario_id: str,
    scenario_name: Optional[str] = None,
    prefix_trace: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Compila una trace normalizzata in uno script Playwright Python.

    - Se prefix_trace è fornita, l'helper do_login_and_go_to_laboratory viene
      generato dalla trace del prefix (stesse strategie/target della run MCP).
    - Altrimenti si usa il template fisso _build_login_helper().

    Nota: la trace contiene SOLO step con esito success (vedi trace_extractor).
    Se durante la run uno step è fallito (es. click_smart sul contatore), la run
    può comunque passare (SOFT_TOOLS / evaluation), ma quello step non entra
    nella trace e quindi non compare nello script generato. Per uno script
    completo, la run MCP deve aver eseguito con successo tutti gli step
    necessari (es. per scenario_2: click su "Campioni con Check-in" prima di
    attendere "Attività di dettaglio dashboard").
    """

    lines: List[str] = []

    # Header imports
    lines.append("import os")
    lines.append("import re")
    lines.append("from pathlib import Path")
    lines.append("from dotenv import load_dotenv")
    lines.append("import pytest")
    lines.append("from playwright.sync_api import Page")
    lines.append("")
    lines.append("# Load backend/.env (parent of generated/)")
    lines.append(
        "load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')"
    )
    lines.append("")

    # Helper login: da trace prefix se disponibile, altrimenti template fisso
    if prefix_trace:
        lines.extend(build_login_helper_from_trace(prefix_trace))
    else:
        lines.extend(_build_login_helper())
    lines.append("")

    # Test function
    test_name = f"test_{scenario_id}"
    display_name = scenario_name or scenario_id

    lines.append("")
    lines.append(f"def {test_name}(page: Page):")
    lines.append(f'    """Scenario: {display_name} ({scenario_id})"""')
    lines.append("    # Perform login and navigate to Laboratory dashboard")
    lines.append("    do_login_and_go_to_laboratory(page)")
    lines.append("")
    lines.append("    # Steps translated from MCP tool trace")

    for step in trace:
        compiled = _compile_step(step)
        if compiled:
            lines.extend(compiled)

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Simple deterministic summary from trace
# ---------------------------------------------------------------------------


def summarize_trace(
    trace: List[Dict[str, Any]],
    scenario_id: str,
    scenario_name: Optional[str] = None,
) -> str:
    """
    Crea una breve descrizione testuale a partire dalla trace (senza usare LLM).

    Esempio:
        "Scenario 'Creazione filtro...' (scenario_1): executed 12 tool steps
         (click_smart=5, fill_smart=3, wait_for_text_content=2); last verification text='Filtro Test'."
    """

    if not trace:
        return f"Scenario {scenario_id}: no tool steps recorded."

    total_steps = len(trace)

    counts: Dict[str, int] = {}
    last_wait_text: Optional[str] = None
    last_get_text: Optional[str] = None

    for step in trace:
        tool = step.get("tool") or "unknown"
        counts[tool] = counts.get(tool, 0) + 1

        args = step.get("args") or {}
        if tool == "wait_for_text_content":
            last_wait_text = args.get("text") or args.get("pattern") or last_wait_text
        elif tool == "get_text_by_visible_content":
            last_get_text = args.get("search_text") or last_get_text

    parts = [f"{name}={count}" for name, count in sorted(counts.items())]
    counts_str = ", ".join(parts)

    name = scenario_name or scenario_id
    base = f"Scenario '{name}' ({scenario_id}): executed {total_steps} tool steps ({counts_str})"

    extra_parts: List[str] = []
    if last_wait_text:
        extra_parts.append(f"last wait_for_text_content='{last_wait_text}'")
    if last_get_text:
        extra_parts.append(f"last get_text_by_visible_content='{last_get_text}'")

    if extra_parts:
        base += "; " + ", ".join(extra_parts)

    return base + "."


# ---------------------------------------------------------------------------
# Helper: login + navigation (da trace prefix o template fisso)
# ---------------------------------------------------------------------------


def _is_username_field(step: Dict[str, Any]) -> bool:
    """True se lo step fill_smart riguarda il campo username."""
    t = (
        step.get("result", {}).get("target")
        or (step.get("args", {}).get("targets") or [{}])[0]
    )
    if not isinstance(t, dict):
        return False
    label = (t.get("label") or t.get("name") or t.get("placeholder") or "").lower()
    return "username" in label or "user" in label or "utente" in label


def _is_password_field(step: Dict[str, Any]) -> bool:
    """True se lo step fill_smart riguarda il campo password."""
    t = (
        step.get("result", {}).get("target")
        or (step.get("args", {}).get("targets") or [{}])[0]
    )
    if not isinstance(t, dict):
        return False
    label = (t.get("label") or t.get("name") or t.get("placeholder") or "").lower()
    return "password" in label or "pwd" in label


def build_login_helper_from_trace(prefix_trace: List[Dict[str, Any]]) -> List[str]:
    """
    Genera l'helper do_login_and_go_to_laboratory dalla trace del prefix (run MCP).
    Usa le stesse strategie/target/fallback della run; credenziali da env (lab_user, lab_password).
    """
    lines: List[str] = []
    lines.append("def do_login_and_go_to_laboratory(page: Page) -> None:")
    lines.append(
        '    """Login to LAB app, select organization, enter Laboratory module (from prefix trace)."""'
    )
    lines.append("    lab_url = os.getenv('LAB_URL')")
    lines.append("    lab_user = os.getenv('LAB_USERNAME')")
    lines.append("    lab_password = os.getenv('LAB_PASSWORD')")
    lines.append("")
    lines.append("    if not lab_url or not lab_user or not lab_password:")
    lines.append(
        "        raise RuntimeError('LAB_URL/LAB_USERNAME/LAB_PASSWORD must be set in environment')"
    )
    lines.append("")
    lines.append("    page.goto(lab_url)")
    lines.append("")

    for step in prefix_trace:
        fill_override: Optional[str] = None
        if step.get("tool") == "fill_smart":
            if _is_username_field(step):
                fill_override = "lab_user"
            elif _is_password_field(step):
                fill_override = "lab_password"
        compiled = _compile_step(step, fill_value_override=fill_override)
        if compiled:
            lines.extend(compiled)

    return lines


def _build_login_helper() -> List[str]:
    """Template helper per login + ingresso nel modulo Laboratory."""
    lines: List[str] = []
    lines.append("def do_login_and_go_to_laboratory(page: Page) -> None:")
    lines.append(
        '    """Login to LAB app, select organization, enter Laboratory module."""'
    )
    lines.append("    lab_url = os.getenv('LAB_URL')")
    lines.append("    lab_user = os.getenv('LAB_USERNAME')")
    lines.append("    lab_password = os.getenv('LAB_PASSWORD')")
    lines.append("")
    lines.append("    if not lab_url or not lab_user or not lab_password:")
    lines.append(
        "        raise RuntimeError('LAB_URL/LAB_USERNAME/LAB_PASSWORD must be set in environment')"
    )
    lines.append("")
    lines.append("    page.goto(lab_url)")
    lines.append("    page.get_by_label('Username').fill(lab_user)")
    lines.append("    page.get_by_label('Password').fill(lab_password)")
    lines.append("    page.get_by_role('button', name='Login').click()")
    lines.append("")
    lines.append("    # Wait for organization selection page")
    lines.append("    try:")
    lines.append(
        "        page.get_by_role('combobox', name='Seleziona Organizzazione').wait_for()"
    )
    lines.append("    except Exception:")
    lines.append(
        "        page.get_by_text('Seleziona Organizzazione').first.wait_for()"
    )
    lines.append("")
    lines.append("    # Wait for Angular spinner to disappear before interacting")
    lines.append(
        "    page.locator('.eng-app-viewport-spinner-container').wait_for(state='hidden', timeout=30000)"
    )
    lines.append("")
    lines.append(
        "    # Select organization (force=True: mat-label can intercept pointer)"
    )
    lines.append(
        "    page.get_by_role('combobox', name='Seleziona Organizzazione').click(force=True)"
    )
    lines.append(
        "    page.get_by_role('option').filter("
        "has_text=re.compile(r'organizzazione.*sistema', re.I)).click()"
    )
    lines.append("    page.get_by_role('button', name='Continua').click()")
    lines.append("")
    lines.append("    # Wait for home tiles and enter Laboratory module")
    lines.append(
        "    page.get_by_role('button', name='Laboratorio Analisi').first.wait_for()"
    )
    lines.append(
        "    page.get_by_role('button', name='Laboratorio Analisi').first.click()"
    )
    lines.append("")
    lines.append("    # Wait for Laboratory module to load (SPA navigation)")
    lines.append("    page.wait_for_load_state('domcontentloaded')")
    lines.append(
        "    page.locator('.eng-app-viewport-spinner-container').wait_for(state='hidden', timeout=30000)"
    )
    lines.append("    # Wait for Laboratory dashboard (Preanalitica tab)")
    lines.append("    page.get_by_text('Preanalitica').first.wait_for(timeout=60000)")
    return lines


# ---------------------------------------------------------------------------
# Compilation of individual steps
# ---------------------------------------------------------------------------


def _compile_step(
    step: Dict[str, Any],
    fill_value_override: Optional[str] = None,
) -> List[str]:
    """
    Traduce un singolo step della trace in codice Playwright.
    Usa result.target / result.strategy / result.fallback_used quando presenti.
    fill_value_override: se impostato e tool=fill_smart, usa questo al posto di value (es. "lab_user").
    """
    tool = step.get("tool", "")
    args = step.get("args") or {}
    result = step.get("result") or {}
    lines: List[str] = []

    if tool == "click_smart":
        targets = args.get("targets") or []
        if _is_icon_only_click(targets):
            return []
        # Preferisci il target che ha effettivamente funzionato in run (dalla trace)
        target = (
            result.get("target") if isinstance(result.get("target"), dict) else None
        )
        if target:
            locator = _locator_from_single_target(target)
        else:
            locator = _pick_locator_from_targets(targets)
        if locator:
            use_force = result.get("click_type") == "js" or result.get("fallback_used")
            strategy_note = result.get("strategy")
            comment = (
                f"    # click_smart (strategy={strategy_note})"
                if strategy_note
                else "    # click_smart"
            )
            lines.append(comment)

            # Se il locator è un get_by_*(...), usa sempre .first per evitare strict mode
            # (es. get_by_role("button", name="Aggiungi filtro") può matchare più elementi).
            def _with_first(loc: str) -> str:
                if (
                    (
                        "get_by_text" in loc
                        or "get_by_role" in loc
                        or "get_by_label" in loc
                        or "get_by_placeholder" in loc
                    )
                    and ".first" not in loc
                    and ".nth(" not in loc
                    and ".last" not in loc
                ):
                    return f"{loc}.first"
                return loc

            if "\n" in locator:
                comment_line, loc = locator.split("\n", 1)
                lines.append(f"    {comment_line}")
                base = _with_first(loc.strip())
                click_call = (
                    f"{base}.click(force=True)" if use_force else f"{base}.click()"
                )
                lines.append(f"    {click_call}")
            else:
                base = _with_first(locator)
                click_call = (
                    f"{base}.click(force=True)" if use_force else f"{base}.click()"
                )
                lines.append(f"    {click_call}")
        else:
            lines.append(
                f"    # TODO: click_smart — locator non risolvibile: {repr(targets)[:120]}"
            )

    elif tool == "fill_smart":
        targets = args.get("targets") or []
        value = args.get("value", "")
        if fill_value_override is not None:
            value_str = fill_value_override
        else:
            value_str = repr(value)
        target = (
            result.get("target") if isinstance(result.get("target"), dict) else None
        )
        if target:
            locator = _locator_from_single_target(target)
        else:
            locator = _pick_locator_from_targets(targets)
        if locator:
            strategy_note = result.get("strategy")
            comment = (
                f"    # fill_smart (strategy={strategy_note})"
                if strategy_note
                else "    # fill_smart"
            )
            lines.append(comment)
            def _with_first(loc: str) -> str:
                if (
                    (
                        "get_by_text" in loc
                        or "get_by_role" in loc
                        or "get_by_label" in loc
                        or "get_by_placeholder" in loc
                    )
                    and ".first" not in loc
                    and ".nth(" not in loc
                    and ".last" not in loc
                ):
                    return f"{loc}.first"
                return loc
            if "\n" in locator:
                comment_line, loc = locator.split("\n", 1)
                lines.append(f"    {comment_line}")
                lines.append(f"    {_with_first(loc.strip())}.fill({value_str})")
            else:
                lines.append(f"    {_with_first(locator)}.fill({value_str})")
        else:
            lines.append(
                f"    # TODO: fill_smart — locator non risolvibile: {repr(targets)[:120]}"
            )

    elif tool == "click_and_wait_for_text":
        targets = args.get("targets") or []
        text = args.get("text", "")
        target = (
            result.get("target") if isinstance(result.get("target"), dict) else None
        )
        locator = (
            _locator_from_single_target(target)
            if target
            else _pick_locator_from_targets(targets)
        )
        if locator:
            lines.append("    # click_and_wait_for_text")
            lines.append(f"    {locator}.click()")
            if text:
                lines.append(f"    page.get_by_text({repr(text)}).first.wait_for()")
        else:
            lines.append(
                f"    # TODO: click_and_wait_for_text — locator non risolvibile: {repr(targets)[:120]}"
            )

    elif tool == "press_key":
        key = args.get("key", "")
        if key:
            lines.append("    # press_key")
            lines.append(f"    page.keyboard.press({repr(key)})")
        else:
            lines.append("    # TODO: press_key senza key")

    elif tool == "wait_for_text_content":
        text = args.get("text") or args.get("pattern")
        if text:
            lines.append("    # wait_for_text_content")
            lines.append(f"    page.get_by_text({repr(text)}).first.wait_for()")
        else:
            lines.append("    # TODO: wait_for_text_content senza text")

    elif tool == "wait_for_element_state":
        targets = args.get("targets") or []
        state = args.get("state", "visible")
        target = (
            result.get("target") if isinstance(result.get("target"), dict) else None
        )
        locator = (
            _locator_from_single_target(target)
            if target
            else _pick_locator_from_targets(targets)
        )
        if locator:
            lines.append("    # wait_for_element_state")
            lines.append(f"    {locator}.wait_for(state={repr(state)})")
        else:
            lines.append(
                f"    # TODO: wait_for_element_state — locator non risolvibile: {repr(targets)[:120]}"
            )

    elif tool == "get_text_by_visible_content":
        search_text = args.get("search_text")
        if search_text:
            lines.append(
                "    # get_text_by_visible_content (valore letto, non assertito)"
            )
            lines.append(
                f"    _tmp_text = page.get_by_text({repr(search_text)}).first.inner_text()"
            )
        else:
            lines.append("    # TODO: get_text_by_visible_content senza search_text")

    elif tool == "wait_for_load_state":
        state = args.get("state", "domcontentloaded")
        lines.append("    # wait_for_load_state")
        lines.append(f"    page.wait_for_load_state({repr(state)})")

    elif tool == "scroll_to_bottom":
        selector = args.get("selector")
        if selector:
            lines.append("    # scroll_to_bottom (container)")
            lines.append(
                f"    page.locator({repr(selector)}).first.evaluate('el => {{ el.scrollTop = el.scrollHeight; }}')"
            )
        else:
            lines.append("    # scroll_to_bottom (window)")
            lines.append(
                "    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')"
            )

    else:
        short_args = repr(args)
        if len(short_args) > 160:
            short_args = short_args[:157] + "..."
        lines.append(f"    # TODO: tool '{tool}' non mappato — args: {short_args}")

    return lines


# ---------------------------------------------------------------------------
# Locator resolution
# ---------------------------------------------------------------------------


def _is_icon_only_click(targets: List[Dict[str, Any]]) -> bool:
    """
    Ritorna True se tutti i targets del click puntano solo a nomi di icone
    Material (testo accessibile dell'icona, non un'azione utente reale).
    """
    if not targets:
        return False
    text_targets = [t for t in targets if isinstance(t, dict) and t.get("by") == "text"]
    non_text_targets = [
        t
        for t in targets
        if isinstance(t, dict) and t.get("by") != "text" and t.get("by") != "tfa"
    ]
    # Se ci sono strategie non-text (role, label...) non è un click-solo-icona
    if non_text_targets:
        return False
    # Se tutti i text targets sono nomi di icone Material
    return all(
        t.get("text", "").lower().strip() in _MATERIAL_ICON_NAMES for t in text_targets
    )


def _unwrap_suggestion(t: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gestisce entrambi i formati targets:

    Formato FLAT (agente → fill_smart/click_smart):
        {"by": "role", "role": "button", "name": "Confirm"}

    Formato NESTED (playwright_suggestions grezzo da inspect):
        {"strategy": "role", "click_smart": {"by": "role", "role": "button", "name": "Confirm"}}
        {"by": "css_id", "fill_smart": {"by": "css", "selector": "#mat-input-19"}}

    Restituisce sempre il dict flat da usare per la risoluzione del locator.
    """
    if not isinstance(t, dict):
        return {}

    # Formato nested con chiave "click_smart" o "fill_smart"
    nested = t.get("click_smart") or t.get("fill_smart")
    if nested and isinstance(nested, dict):
        return nested

    # Già flat
    return t


def _locator_from_single_target_inner(t: Dict[str, Any]) -> Optional[str]:
    """
    Restituisce la parte finale del locator SENZA prefisso 'page.'
    Es: get_by_role('button', name='Aggiungi filtro')
    Usato sia da _locator_from_single_target che dalla variante scoped.
    """
    by = t.get("by")
    if by == "role" and t.get("role"):
        return f"get_by_role({repr(t['role'])}, name={repr(t.get('name') or '')})"
    if by == "label" and t.get("label"):
        return f"get_by_label({repr(t['label'])})"
    if by == "placeholder" and t.get("placeholder"):
        return f"get_by_placeholder({repr(t['placeholder'])})"
    if by == "text" and t.get("text"):
        return f"get_by_text({repr(t['text'])})"
    if by == "tfa" and t.get("tfa"):
        return f"locator('[data-tfa={repr(t['tfa'])}]')"
    if by in {"css", "css_id", "css_aria", "css_row"} and t.get("selector"):
        sel = t["selector"]
        if "mat-input" in sel:
            return f"# WARNING: Angular dynamic ID, potrebbe cambiare tra run\n    locator({repr(sel)})"
        return f"locator({repr(sel)})"
    if by == "xpath" and t.get("xpath"):
        return f"locator('xpath={t['xpath']}')"
    return None


def _locator_from_single_target(t: Dict[str, Any]) -> Optional[str]:
    """
    Costruisce una riga di codice Playwright per un singolo target flat
    (es. result.target dalla trace).

    Se il target contiene un campo 'scope' (aggiunto da click_smart quando
    il locator matcha più elementi), genera un locator scoped:
        page.locator('card-group').last.get_by_role('button', name='Aggiungi filtro')
    altrimenti genera il locator globale standard:
        page.get_by_role('button', name='Aggiungi filtro')
    """
    if not t or not isinstance(t, dict):
        return None

    inner = _locator_from_single_target_inner(t)
    if not inner:
        return None

    # Se inner è multi-linea (warning + locator), evita di prefissare due volte "page."
    if "\n" in inner:
        comment_line, loc = inner.split("\n", 1)
        loc_str = loc.strip()
        if not loc_str.startswith("page."):
            loc_str = f"page.{loc_str}"
        return f"{comment_line}\n    {loc_str}"

    scope = t.get("scope")
    if scope and isinstance(scope, dict):
        sel = scope.get("selector")
        idx = scope.get("index", 0)
        total = scope.get("total", 1)
        if sel:
            # Se è l'ultimo elemento usa .last (più stabile di .nth quando si aggiungono gruppi)
            if idx == total - 1:
                scope_loc = f"page.locator({repr(sel)}).last"
            else:
                scope_loc = f"page.locator({repr(sel)}).nth({idx})"
            return f"{scope_loc}.{inner}"

    # Nessuno scope: locator globale con prefisso page.
    return f"page.{inner}"


def _pick_locator_from_targets(targets: List[Dict[str, Any]]) -> Optional[str]:
    """
    Sceglie il primo locator stabile dalla lista targets.
    Priorità: role > label > placeholder > text > tfa > css
    Gestisce sia il formato flat che il formato playwright_suggestions nested.
    """
    flat_targets = [_unwrap_suggestion(t) for t in targets]
    for t in flat_targets:
        loc = _locator_from_single_target(t)
        if loc:
            return loc
    return None
