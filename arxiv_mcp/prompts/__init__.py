from .analysis import register_prompts as register_analysis_prompts
from .discovery import register_prompts as register_discovery_prompts
from .evaluation import register_prompts as register_evaluation_prompts
from .learning import register_prompts as register_learning_prompts
from .synthesis import register_prompts as register_synthesis_prompts


def register_prompts(mcp):
    register_learning_prompts(mcp)
    register_synthesis_prompts(mcp)
    register_analysis_prompts(mcp)
    register_discovery_prompts(mcp)
    register_evaluation_prompts(mcp)