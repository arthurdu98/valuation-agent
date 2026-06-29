from pydantic import BaseModel, Field
import yaml
from pathlib import Path


class ModelConfig(BaseModel):
    provider: str  # openai | anthropic | openai_compatible | ollama
    model_name: str
    base_url: str | None = None
    api_key_env: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


class LLMConfig(BaseModel):
    default_model: str
    models: dict[str, ModelConfig]
    role_routing: dict[str, str] = Field(default_factory=dict)
    fallback_chain: list[str] = Field(default_factory=list)


def load_llm_config(config_path: str = "configs/llm.yaml") -> LLMConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"LLM config not found: {config_path}")
    with open(path) as f:
        raw = yaml.safe_load(f)
    models = {name: ModelConfig(**cfg) for name, cfg in raw.get("models", {}).items()}
    return LLMConfig(
        default_model=raw.get("default_model", ""),
        models=models,
        role_routing=raw.get("role_routing", {}),
        fallback_chain=raw.get("fallback_chain", []),
    )
