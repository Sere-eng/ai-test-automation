import os
import re
from pathlib import Path
from dotenv import load_dotenv
import pytest
from playwright.sync_api import Page

# Load backend/.env (parent of generated/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

def do_login_and_go_to_laboratory(page: Page) -> None:
    """Login to LAB app, select organization, enter Laboratory module."""
    lab_url = os.getenv('LAB_URL')
    lab_user = os.getenv('LAB_USERNAME')
    lab_password = os.getenv('LAB_PASSWORD')

    if not lab_url or not lab_user or not lab_password:
        raise RuntimeError('LAB_URL/LAB_USERNAME/LAB_PASSWORD must be set in environment')

    page.goto(lab_url)
    page.get_by_label('Username').fill(lab_user)
    page.get_by_label('Password').fill(lab_password)
    page.get_by_role('button', name='Login').click()

    # Wait for organization selection page
    try:
        page.get_by_role('combobox', name='Seleziona Organizzazione').wait_for()
    except Exception:
        page.get_by_text('Seleziona Organizzazione').first.wait_for()

    # Wait for Angular spinner to disappear before interacting
    page.locator('.eng-app-viewport-spinner-container').wait_for(state='hidden', timeout=30000)

    # Select organization (force=True: mat-label can intercept pointer)
    page.get_by_role('combobox', name='Seleziona Organizzazione').click(force=True)
    page.get_by_role('option').filter(has_text=re.compile(r'organizzazione.*sistema', re.I)).click()
    page.get_by_role('button', name='Continua').click()

    # Wait for home tiles and enter Laboratory module
    page.get_by_role('button', name='Laboratorio Analisi').first.wait_for()
    page.get_by_role('button', name='Laboratorio Analisi').first.click()

    # Wait for Laboratory module to load (SPA navigation)
    page.wait_for_load_state('domcontentloaded')
    page.locator('.eng-app-viewport-spinner-container').wait_for(state='hidden', timeout=30000)
    # Wait for Laboratory dashboard (Preanalitica tab)
    page.get_by_text('Preanalitica').first.wait_for(timeout=60000)


def test_scenario_5(page: Page):
    """Scenario: SMPLIST_001 - Dashboard, elenco campione e dettaglio campione - Scenario 5 (scenario_5)"""
    # Perform login and navigate to Laboratory dashboard
    do_login_and_go_to_laboratory(page)

    # Steps translated from MCP tool trace
    # click_smart (strategy=role)
    page.get_by_role('button', name='Laboratorio').first.click()
    # wait_for_load_state
    page.wait_for_load_state('domcontentloaded')
    # click_smart (strategy=role)
    page.get_by_role('button', name='Modifica').first.click()
    # click_smart (strategy=text)
    page.get_by_text('AGGIUNGI GRUPPO').first.click()
    # fill_smart (strategy=css)
    # WARNING: Angular dynamic ID, potrebbe cambiare tra run
    page.locator('#mat-input-19').fill('Gruppo_AUTO_TEST')
    # click_smart (strategy=role)
    page.locator('card-group').nth(0).get_by_role('button', name='Aggiungi filtro').click()
    # fill_smart (strategy=label)
    page.get_by_label('Nome filtro*').first.fill('AUTO_PL_20231010')
    # fill_smart (strategy=label)
    page.get_by_label('Descrizione').first.fill('Creato da test automatico')
    # click_smart (strategy=role)
    page.get_by_role('combobox', name='Piano di lavoro').first.click()
    # click_smart (strategy=role)
    page.get_by_role('option', name='-- BaggiovaraTossicologia [BAG-TOS]').first.click()
    # click_smart (strategy=role)
    page.get_by_role('button', name='Conferma').first.click(force=True)
    # wait_for_text_content
    page.get_by_text('AUTO_PL_20231010').first.wait_for()
