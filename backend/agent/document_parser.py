# backend/agent/document_parser.py
"""
Parser per documenti di test (Word, HTML).
Estrae sezioni strutturate da documenti JIRA esportati o test case manuali.
"""

import re
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup
import chardet


class TestDocumentParser:
    """Parser per documenti di test case in vari formati."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = None
        self.soup = None
        
    def parse(self) -> Dict[str, str]:
        """
        Estrae le sezioni principali dal documento.
        
        Returns:
            Dict con chiavi: title, initial_conditions, test_steps, expected_results, raw_html
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"File non trovato: {self.file_path}")
        
        # Leggi il file con encoding detection
        raw_bytes = self.file_path.read_bytes()
        detected = chardet.detect(raw_bytes)
        encoding = detected['encoding'] or 'utf-8'
        
        try:
            self.content = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            # Fallback a latin-1 se UTF-8 fallisce
            self.content = raw_bytes.decode('latin-1')
        
        # Determina il tipo di file
        if self._is_html():
            return self._parse_html()
        elif self.file_path.suffix.lower() in ['.docx']:
            return self._parse_docx()
        else:
            # File .doc che in realtà è HTML (come quelli esportati da JIRA)
            return self._parse_html()
    
    def _is_html(self) -> bool:
        """Verifica se il contenuto è HTML."""
        return bool(re.search(r'<html|<HTML|<!DOCTYPE', self.content[:500]))
    
    def _parse_html(self) -> Dict[str, str]:
        """
        Estrae informazioni da HTML (tipicamente export JIRA).
        
        Cerca:
        - Titolo (h3.formtitle o primo h3)
        - Condizioni Iniziali (td con "Condizioni Iniziali")
        - Passi del Test (td con "Passi del Test")
        - Condizioni Finali (td con "Condizioni Finali")
        """
        self.soup = BeautifulSoup(self.content, 'html.parser')
        
        result = {
            'title': self._extract_title(),
            'initial_conditions': self._extract_section('Condizioni Iniziali', 'Dati di input'),
            'test_steps': self._extract_section('Passi del Test', 'Modalità di esecuzione'),
            'expected_results': self._extract_section('Condizioni Finali', 'Risultati attesi'),
            'raw_html': self.content,
            'format': 'html'
        }
        
        return result
    
    def _parse_docx(self) -> Dict[str, str]:
        """
        Estrae informazioni da file Word .docx.
        Richiede python-docx.
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx non installato. Installa con: pip install python-docx"
            )
        
        doc = Document(self.file_path)
        
        # Estrai tutto il testo
        full_text = '\n'.join([para.text for para in doc.paragraphs])
        
        # Pattern per trovare sezioni
        sections = {
            'title': self._extract_docx_section(full_text, r'^(.+?)$', first_line=True),
            'initial_conditions': self._extract_docx_section(
                full_text, 
                r'(?:Condizioni Iniziali|Prerequisiti)[:\s]+(.*?)(?=Condizioni Finali|Passi del Test|Modalità|$)',
                re.DOTALL | re.IGNORECASE
            ),
            'test_steps': self._extract_docx_section(
                full_text,
                r'(?:Passi del Test|Modalità di esecuzione)[:\s]+(.*?)(?=Condizioni Finali|Risultati attesi|Dati di input|$)',
                re.DOTALL | re.IGNORECASE
            ),
            'expected_results': self._extract_docx_section(
                full_text,
                r'(?:Condizioni Finali|Risultati attesi)[:\s]+(.*?)(?=Dati di input|$)',
                re.DOTALL | re.IGNORECASE
            ),
            'raw_text': full_text,
            'format': 'docx'
        }
        
        return sections
    
    def _extract_title(self) -> str:
        """Estrae il titolo dal documento HTML."""
        # Prova h3.formtitle
        title_elem = self.soup.find('h3', class_='formtitle')
        if title_elem:
            # Rimuovi il ticket ID tipo [HC40DIAGOL-7155]
            text = title_elem.get_text(strip=True)
            text = re.sub(r'\[.*?\]\s*', '', text)
            return text
        
        # Fallback: primo h3
        h3 = self.soup.find('h3')
        if h3:
            text = h3.get_text(strip=True)
            text = re.sub(r'\[.*?\]\s*', '', text)
            return text
        
        # Fallback: title tag
        title = self.soup.find('title')
        if title:
            text = title.get_text(strip=True)
            text = re.sub(r'\[.*?\]\s*', '', text)
            return text
        
        return "Untitled"
    
    def _extract_section(self, *labels: str) -> str:
        """
        Estrae una sezione dal documento HTML cercando label specifiche.
        
        Args:
            *labels: Una o più label da cercare (es. "Condizioni Iniziali", "Prerequisiti")
        
        Returns:
            Testo della sezione pulito
        """
        for label in labels:
            # Cerca td con il label in bold
            cells = self.soup.find_all('td', bgcolor="#f0f0f0")
            for cell in cells:
                b_tag = cell.find('b')
                if b_tag and label.lower() in b_tag.get_text(strip=True).lower():
                    # Trova la cella successiva (stesso tr)
                    tr = cell.parent
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        content_cell = tds[1]
                        return self._clean_html_text(content_cell)
        
        return ""
    
    def _clean_html_text(self, element) -> str:
        """
        Pulisce il testo HTML rimuovendo tag ma preservando struttura liste.
        """
        if not element:
            return ""
        
        # Sostituisci <li> con bullet point
        for li in element.find_all('li'):
            li.insert(0, '• ')
        
        # Sostituisci <p> con newline
        for p in element.find_all('p'):
            p.append('\n')
        
        # Estrai testo
        text = element.get_text(separator='\n', strip=True)
        
        # Pulisci spazi multipli
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _extract_docx_section(self, text: str, pattern: str, flags=0, first_line=False) -> str:
        """Helper per estrarre sezioni da testo .docx con regex."""
        if first_line:
            lines = text.split('\n')
            return lines[0] if lines else ""
        
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip() if match.lastindex else match.group(0).strip()
        return ""
    
    def extract_scenarios(self) -> list[Dict[str, str]]:
        """
        Estrae gli scenari individuali dal documento.
        Ogni scenario contiene: id, name, steps, expected_results.
        
        Returns:
            Lista di dict con scenari
        """
        data = self.parse()
        test_steps = data.get("test_steps", "")
        expected_results = data.get("expected_results", "")
        
        # Identifica scenari (Nel primo scenario, Nel secondo scenario, etc.)
        scenario_pattern = r'Nel (primo|secondo|terzo|quarto|quinto|sesto|settimo|ottavo|nono|decimo) scenario:'
        step_parts = re.split(scenario_pattern, test_steps, flags=re.IGNORECASE)
        result_parts = re.split(scenario_pattern, expected_results, flags=re.IGNORECASE)
        
        scenarios = []
        scenario_map = {
            "primo": 1, "secondo": 2, "terzo": 3, "quarto": 4, "quinto": 5,
            "sesto": 6, "settimo": 7, "ottavo": 8, "nono": 9, "decimo": 10
        }
        
        # Combina step e risultati
        i = 1
        while i < len(step_parts):
            if i + 1 < len(step_parts):
                scenario_name = step_parts[i].strip().lower()
                scenario_steps = step_parts[i + 1].strip()
                
                # Trova risultati corrispondenti
                scenario_results = ""
                try:
                    result_idx = result_parts.index(scenario_name)
                    if result_idx + 1 < len(result_parts):
                        scenario_results = result_parts[result_idx + 1].strip()
                except ValueError:
                    pass
                
                scenario_num = scenario_map.get(scenario_name, i // 2 + 1)
                
                # Parse steps in lista
                steps_list = self._parse_bullet_list(scenario_steps)
                
                scenarios.append({
                    "id": f"scenario_{scenario_num}",
                    "name": f"Scenario {scenario_num} (extracted)",
                    "execution_steps": steps_list,
                    "expected_results": [scenario_results] if scenario_results else [],
                    "prompt_hints": None
                })
            i += 2
        
        return scenarios
    
    def _parse_bullet_list(self, text: str) -> list[str]:
        """Converte testo con bullet in lista di stringhe."""
        lines = text.split('\n')
        items = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Rimuovi bullet markers
            line = re.sub(r'^[•\-\*]\s*', '', line)
            if line:
                items.append(line)
        return items


def parse_test_document(file_path: str) -> Dict[str, str]:
    """
    Funzione di convenienza per parsare un documento.
    
    Args:
        file_path: Percorso al file da parsare
    
    Returns:
        Dict con sezioni estratte
    """
    parser = TestDocumentParser(file_path)
    return parser.parse()


# === CLI per testing ===
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Uso: python document_parser.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        result = parse_test_document(file_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Errore: {e}")
        sys.exit(1)
