# backend/agent/setup.py
"""
Setup LLM e MCP per l'agent. Configurazione centralizzata da AppConfig.
"""
import os
import sys

from config.settings import AppConfig
from langchain_openai import ChatOpenAI, AzureChatOpenAI


def create_llm():
    """Crea l'istanza LLM da AppConfig (OpenRouter, Azure o OpenAI)."""
    provider = AppConfig.LLM.get_provider()

    if provider == "openrouter":
        return ChatOpenAI(
            model=AppConfig.LLM.OPENROUTER_MODEL,
            api_key=AppConfig.LLM.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=AppConfig.LLM.TEMPERATURE,
            max_tokens=AppConfig.LLM.MAX_TOKENS,
        )
    if provider == "azure":
        return AzureChatOpenAI(
            azure_endpoint=AppConfig.LLM.AZURE_ENDPOINT,
            azure_deployment=AppConfig.LLM.AZURE_DEPLOYMENT,
            api_version=AppConfig.LLM.AZURE_API_VERSION,
            api_key=AppConfig.LLM.AZURE_API_KEY,
            temperature=AppConfig.LLM.TEMPERATURE,
            max_tokens=AppConfig.LLM.MAX_TOKENS,
        )
    # default: openai
    return ChatOpenAI(
        model=AppConfig.LLM.OPENAI_MODEL,
        api_key=AppConfig.LLM.OPENAI_API_KEY,
        temperature=AppConfig.LLM.TEMPERATURE,
        max_tokens=AppConfig.LLM.MAX_TOKENS,
    )


def create_mcp_config(use_remote: bool):
    """Crea la config MCP (remoto HTTP o locale stdio)."""
    if use_remote:
        return {
            "playwright": {
                "url": AppConfig.MCP.get_remote_url(),
                "transport": "streamable_http",
            }
        }
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(
        os.path.dirname(script_dir),
        "mcp_servers",
        "playwright_server_local.py",
    )
    return {
        "playwright": {
            "command": sys.executable,
            "args": [server_path],
            "transport": "stdio",
        }
    }
