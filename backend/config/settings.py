# backend/config/settings.py
"""
Configurazione centralizzata per AI Test Automation.
Tutte le impostazioni in un unico posto.
"""
import os
from dotenv import load_dotenv
from typing import Literal, Tuple

load_dotenv()


class MCPConfig:
    """Configurazione MCP Server"""

    # ======================================================
    # MCP MODE: "local" per stdio, "remote" per HTTP remoto
    # ======================================================
    MODE: Literal["local", "remote"] = os.getenv("MCP_MODE", "remote").strip().lower()

    # Configurazione server remoto
    REMOTE_HOST = os.getenv("MCP_REMOTE_HOST", "localhost")
    REMOTE_PORT = int(os.getenv("MCP_REMOTE_PORT", "8001"))

    @classmethod
    def use_remote(cls) -> bool:
        """Returns True if using remote MCP server"""
        return cls.MODE == "remote"

    @classmethod
    def get_remote_url(cls) -> str:
        """Get remote server URL"""
        return f"http://{cls.REMOTE_HOST}:{cls.REMOTE_PORT}/mcp/"

    @classmethod
    def validate(cls):
        """Valida la configurazione"""
        if cls.MODE not in ["local", "remote"]:
            raise ValueError(
                f"MCP_MODE deve essere 'local' o 'remote', non '{cls.MODE}'"
            )

        if cls.use_remote():
            print(
                f"MCP Mode: REMOTE - Assicurati che il server sia attivo su {cls.get_remote_url()}"
            )
        else:
            print(f"MCP Mode: LOCAL (stdio)")


class LLMConfig:
    """Configurazione LLM Provider"""

    # OpenRouter (priorità 1)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL", "openai/gpt-4o-mini"
    )  # Default: openai/gpt-4o-mini

    # Azure OpenAI (priorità 2)
    AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    # OpenAI Standard (priorità 3)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4o-mini"

    # Ollama (priorità 4)
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")

    # Temperature (determinismo)
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8000"))

    @classmethod
    def get_provider(cls) -> Literal["openrouter", "azure", "openai"]:
        """Determina quale provider usare (priority order)"""
        if cls.OPENROUTER_API_KEY and cls.OPENROUTER_MODEL:
            return "openrouter"
        elif cls.AZURE_API_KEY and cls.AZURE_ENDPOINT and cls.AZURE_DEPLOYMENT:
            return "azure"
        elif cls.OPENAI_API_KEY:
            return "openai"
        elif cls.OLLAMA_ENDPOINT:
            return "ollama"
        else:
            raise ValueError(
                "Nessuna API key configurata!\n"
                "Configura .env con una di queste:\n"
                "  - OPENROUTER_API_KEY + OPENROUTER_MODEL\n"
                "  - OPENAI_API_KEY\n"
                "  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT_NAME\n"
                "  - OLLAMA_ENDPOINT + OLLAMA_MODEL"
            )

    @classmethod
    def validate(cls):
        """Valida che almeno un provider sia configurato"""
        provider = cls.get_provider()
        print(f"LLM Provider: {provider.upper()}")

        if provider == "openrouter":
            print(f"   Model: {cls.OPENROUTER_MODEL}")
        elif provider == "azure":
            print(f"   Endpoint: {cls.AZURE_ENDPOINT}")
            print(f"   Deployment: {cls.AZURE_DEPLOYMENT}")
        elif provider == "openai":
            print(f"   Model: {cls.OPENAI_MODEL}")


class PlaywrightConfig:
    """Configurazione Playwright Browser"""

    HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))
    VIEWPORT_WIDTH = int(os.getenv("PLAYWRIGHT_VIEWPORT_WIDTH", "1400"))
    VIEWPORT_HEIGHT = int(os.getenv("PLAYWRIGHT_VIEWPORT_HEIGHT", "950"))
    LOCALE = os.getenv("PLAYWRIGHT_LOCALE", "it-IT")
    TIMEZONE = os.getenv("PLAYWRIGHT_TIMEZONE", "Europe/Rome")

    # Registro incrementale per inspect_interactive_elements / inspect_region:
    # blocchi custom (spesso div / web component) che il nucleo in tools.py non include.
    # Estendere quando una run fallisce la discovery; evitare .pointer globale fuori da inspect_region.
    # Nota: righe tabella (mat-row, tr in tbody, …) sono già gestite a parte in tools.py (pass 2b).
    _INSPECT_EXTRA_CLICKABLE_DEFAULTS: Tuple[str, ...] = (
        # UNITY – KPI circolari dashboard (solo contatori cliccabili)
        "div.circle-card.pointer",
        # Griglia tile home (app-home-activity); copre anche tile senza role="button" nel markup
        "div.home-app[tabindex='0']",
        # Stessa tile se usano tabindex vuoto esplicito
        'div.home-app[tabindex=""]',
        # Card contenitore con classi Angular dinamiche ma token circle-card stabile
        "div[class*='circle-card'].pointer",
        # Pannello espandibile Material (header cliccabile, spesso non è <button>)
        "mat-expansion-panel-header",
        # Voci menu/lista come link (nav / impostazioni)
        "a.mat-mdc-list-item",
        # Chip / opzioni filtro selezionabili (MDC)
        "mat-chip-option",
    )

    # scroll_to_bottom: il selettore `.sample-table-container` compare due volte nel DOM (wrapper vs
    # contenitore interno). Se l’agent passa uno di questi alias, il tool scrolla la lista reale e
    # porta in vista il riepilogo righe in fondo pagina.
    _SCROLL_SAMPLE_TABLE_WRAPPER_ALIASES: Tuple[str, ...] = (
        ".sample-table-container",
        ".table.sample-table-container",
        "div.sample-table-container",
        "div.table.sample-table-container",
    )
    _SCROLL_SAMPLE_TABLE_LIST_LOCATOR: str = "sample-table div.search-results"
    _SCROLL_SAMPLE_TABLE_FOOTER_TEXT: str = "Totale righe visualizzate"

    @classmethod
    def is_scroll_sample_table_wrapper(cls, selector: str) -> bool:
        return selector.strip() in cls._SCROLL_SAMPLE_TABLE_WRAPPER_ALIASES

    @classmethod
    def get_scroll_sample_table_list_locator(cls) -> str:
        return cls._SCROLL_SAMPLE_TABLE_LIST_LOCATOR

    @classmethod
    def get_scroll_sample_table_footer_text(cls) -> str:
        return cls._SCROLL_SAMPLE_TABLE_FOOTER_TEXT

    @classmethod
    def get_inspect_extra_clickable_selectors(cls) -> Tuple[str, ...]:
        """
        Default del registro + valori aggiuntivi da .env (comma-separated).
        Esempio: INSPECT_EXTRA_CLICKABLE_SELECTORS=div.my-tile.pointer,tr.clickable-row
        """
        raw = os.getenv("INSPECT_EXTRA_CLICKABLE_SELECTORS", "").strip()
        env_extras = [p.strip() for p in raw.split(",") if p.strip()]
        seen: set[str] = set()
        merged: list[str] = []
        for s in list(cls._INSPECT_EXTRA_CLICKABLE_DEFAULTS) + env_extras:
            if s not in seen:
                seen.add(s)
                merged.append(s)
        return tuple(merged)


class FlaskConfig:
    """Configurazione Flask Server"""

    HOST = os.getenv("FLASK_HOST", "localhost")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    ENV = os.getenv("FLASK_ENV", "development")


class AMCConfig:
    """Configurazione per test login AMC"""

    # URL principale fornita nel test
    URL = os.getenv(
        "AMC_URL",
        "https://amc.eng.it/multimodule/web/",
    )
    USERNAME = os.getenv("AMC_USERNAME", "")
    PASSWORD = os.getenv("AMC_PASSWORD", "")

    @classmethod
    def validate(cls):
        """Valida che le credenziali siano configurate"""
        if not cls.USERNAME or not cls.PASSWORD:
            return False
        return True


class LABConfig:
    """Configurazione per test Laboratory / Clinical Laboratory"""

    # URL principale fornita nel test
    URL = os.getenv(
        "LAB_URL",
        "https://mdrsanitalab2.eng.it/multimodule/ELLIPSE_LAB/?ENGAPPCONFIGS=%7B%22ENG_APP_DISABLE_DATA_PROFILER%22%3Atrue%2C%22ENG_APP_DISABLE_ACTIVITY_PROFILER%22%3Atrue%2C%22ENG_APP_DISABLE_MENU_PROFILER%22%3Atrue%7D",
    )

    USERNAME = os.getenv("LAB_USERNAME", "")
    PASSWORD = os.getenv("LAB_PASSWORD", "")

    @classmethod
    def validate(cls):
        """Facoltativo: le credenziali LAB potrebbero non essere sempre configurate"""
        if not cls.USERNAME or not cls.PASSWORD:
            return False
        return True


class AgentConfig:
    """Configurazione Agent LangGraph"""

    RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "80"))

    # Tool usage preferences
    ALWAYS_INSPECT_AFTER_NAVIGATION = True
    ALWAYS_WAIT_FOR_LOAD_STATE = True
    DEFAULT_TIMEOUT_PER_TRY = 2000  # ms per ogni strategia in click_smart/fill_smart


class AppConfig:
    """Configurazione globale dell'applicazione"""

    MCP = MCPConfig
    LLM = LLMConfig
    PLAYWRIGHT = PlaywrightConfig
    FLASK = FlaskConfig
    AMC = AMCConfig
    LAB = LABConfig
    AGENT = AgentConfig

    @classmethod
    def validate_all(cls):
        """Valida tutta la configurazione all'avvio"""
        print("\n" + "=" * 80)
        print("VALIDAZIONE CONFIGURAZIONE")
        print("=" * 80)

        cls.MCP.validate()
        cls.LLM.validate()
        cls.AMC.validate()

        print(f"Flask: {cls.FLASK.HOST}:{cls.FLASK.PORT}")
        print(f"Playwright: headless={cls.PLAYWRIGHT.HEADLESS}")
        print(f"Agent: recursion_limit={cls.AGENT.RECURSION_LIMIT}")
        print("=" * 80 + "\n")


# Valida configurazione all'import quando il modulo viene importato da altri file
# if __name__ != "__main__":
#     AppConfig.validate_all()
