from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from agent.setup import create_llm, create_mcp_config
from config.settings import AppConfig
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


@dataclass
class MCPAgentRuntime:
    """
    Runtime condiviso per:
    - LLM (provider/config da AppConfig)
    - MCP client + tool discovery
    - cache dei grafi/agent per prompt

    Obiettivo: evitare re-init e doppia discovery tool tra prefix/scenario/execution.
    """

    llm: Any = field(default_factory=create_llm)
    use_remote: bool = field(default_factory=lambda: AppConfig.MCP.use_remote())
    mcp_config: Dict[str, Any] = field(init=False)

    client: Optional[MultiServerMCPClient] = None
    tools: list[Any] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)

    _initialized: bool = False
    _agent_cache: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.mcp_config = create_mcp_config(self.use_remote)

    async def ensure_initialized(self) -> None:
        if self._initialized:
            return

        self.client = MultiServerMCPClient(self.mcp_config)
        tools = await self.client.get_tools()
        self.tools = tools
        self.tool_names = [t.name for t in tools]

        self._initialized = True

    def get_agent_for_prompt(self, prompt: str):
        """
        Restituisce un agent ReAct per uno specifico system prompt, con caching.
        """
        if prompt in self._agent_cache:
            return self._agent_cache[prompt]
        agent = create_react_agent(self.llm, self.tools, prompt=prompt)
        self._agent_cache[prompt] = agent
        return agent

