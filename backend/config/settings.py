# backend/config/settings.py
"""
Configurazione centralizzata per AI Test Automation.
Tutte le impostazioni in un unico posto.
"""
import os
from dotenv import load_dotenv
from typing import Literal

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
            raise ValueError(f"MCP_MODE deve essere 'local' o 'remote', non '{cls.MODE}'")
        
        if cls.use_remote():
            print(f"MCP Mode: REMOTE - Assicurati che il server sia attivo su {cls.get_remote_url()}")
        else:
            print(f"MCP Mode: LOCAL (stdio)")


class LLMConfig:
    """Configurazione LLM Provider"""
    
    # OpenRouter (priorità 1)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    
    # Azure OpenAI (priorità 2)
    AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    
    # OpenAI Standard (priorità 3)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4o-mini"
    
    # Temperature (determinismo)
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    @classmethod
    def get_provider(cls) -> Literal["openrouter", "azure", "openai"]:
        """Determina quale provider usare (priority order)"""
        if cls.OPENROUTER_API_KEY and cls.OPENROUTER_MODEL:
            return "openrouter"
        elif cls.AZURE_API_KEY and cls.AZURE_ENDPOINT and cls.AZURE_DEPLOYMENT:
            return "azure"
        elif cls.OPENAI_API_KEY:
            return "openai"
        else:
            raise ValueError(
                "Nessuna API key configurata!\n"
                "Configura .env con una di queste:\n"
                "  - OPENROUTER_API_KEY + OPENROUTER_MODEL\n"
                "  - OPENAI_API_KEY\n"
                "  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT_NAME"
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
    VIEWPORT_WIDTH = int(os.getenv("PLAYWRIGHT_VIEWPORT_WIDTH", "1920"))
    VIEWPORT_HEIGHT = int(os.getenv("PLAYWRIGHT_VIEWPORT_HEIGHT", "1080"))
    LOCALE = os.getenv("PLAYWRIGHT_LOCALE", "it-IT")
    TIMEZONE = os.getenv("PLAYWRIGHT_TIMEZONE", "Europe/Rome")


class FlaskConfig:
    """Configurazione Flask Server"""
    
    HOST = os.getenv("FLASK_HOST", "localhost")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    ENV = os.getenv("FLASK_ENV", "development")


class AMCConfig:
    """Configurazione per test login AMC"""
    
    URL = "https://amc.eng.it/multimodule/web/"
    USERNAME = os.getenv("AMC_USERNAME", "")
    PASSWORD = os.getenv("AMC_PASSWORD", "")
    
    # Selettori verificati dall'ispezione
    # USERNAME_SELECTOR = "input[name='username']"
    # PASSWORD_SELECTOR = "input[name='password']"
    # LOGIN_BUTTON_SELECTOR = "button:has-text('Login')"  # Oppure 'Accedi'
    
    # Opzionale: checkbox profilo predefinito
    # USE_DEFAULT_PROFILE_CHECKBOX = "input[name='useDefaultProfiling']"
    
    @classmethod
    def validate(cls):
        """Valida che le credenziali siano configurate"""
        if not cls.USERNAME or not cls.PASSWORD:
            return False
        return True
    
class AgentConfig:
    RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "25"))


class AppConfig:
    """Configurazione globale dell'applicazione"""
    
    MCP = MCPConfig
    LLM = LLMConfig
    PLAYWRIGHT = PlaywrightConfig
    FLASK = FlaskConfig
    AMC = AMCConfig
    AGENT = AgentConfig
    
    @classmethod
    def validate_all(cls):
        """Valida tutta la configurazione all'avvio"""
        print("\n" + "=" * 80)
        print("VALIDAZIONE CONFIGURAZIONE")
        print("=" * 80)
        
        cls.MCP.validate()
        cls.LLM.validate()
        
        print(f"Flask: {cls.FLASK.HOST}:{cls.FLASK.PORT}")
        print(f"Playwright: headless={cls.PLAYWRIGHT.HEADLESS}")
        print("=" * 80 + "\n")


# Valida configurazione all'import quando il modulo viene importato da altri file
# if __name__ != "__main__":
#     AppConfig.validate_all()