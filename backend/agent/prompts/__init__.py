from agent.prompts.amc import AMC_SYSTEM_PROMPT, get_amc_optimized_prompt
from agent.prompts.lab import LAB_SYSTEM_PROMPT, get_lab_optimized_prompt
from agent.prompts.lab_prefix import build_lab_prefix_prompt, get_prefix_prompt
from agent.prompts.extraction import EXTRACTION_SYSTEM_PROMPT

__all__ = [
    "AMC_SYSTEM_PROMPT",
    "get_amc_optimized_prompt",
    "LAB_SYSTEM_PROMPT",
    "get_lab_optimized_prompt",
    "build_lab_prefix_prompt",
    "get_prefix_prompt",
    "EXTRACTION_SYSTEM_PROMPT",
]

