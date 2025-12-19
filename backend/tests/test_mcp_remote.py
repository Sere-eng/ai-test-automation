# test_mcp_remote.py
"""
Script per testare il server MCP remoto.
Verifica connessione e lista i tool disponibili.
"""

import asyncio
import sys
import os

# Aggiungi la directory parent al path per gli import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_mcp_adapters.client import MultiServerMCPClient
from config.settings import AppConfig


async def test_remote_server():
    """Testa la connessione al server MCP remoto"""
    
    print("=" * 80)
    print("TEST MCP REMOTE SERVER")
    print("=" * 80)
    print(f"URL: {AppConfig.MCP.get_remote_url()}")
    print("=" * 80 + "\n")
    
    # Configurazione client
    mcp_config = {
        "playwright": {
            "url": AppConfig.MCP.get_remote_url(),
            "transport": "streamable_http",
        }
    }
    
    print("Connessione al server MCP remoto...")
    
    try:
        # Crea il client
        client = MultiServerMCPClient(mcp_config)
        
        # Carica i tool
        print("Caricamento tool...\n")
        tools = await client.get_tools()
        
        print(f"SERVER REMOTO FUNZIONA!")
        print(f"{len(tools)} tool caricati:\n")
        
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.name}")
            if hasattr(tool, 'description'):
                print(f"      → {tool.description[:80]}...")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETATO CON SUCCESSO")
        print("=" * 80)
        
    except Exception as e:
        print(f"ERRORE nella connessione:")
        print(f"   {type(e).__name__}: {e}")
        print("\nAssicurati che il server remoto sia attivo:")
        print(f"   python mcp_servers/playwright_server_remote.py")


if __name__ == "__main__":
    asyncio.run(test_remote_server())
