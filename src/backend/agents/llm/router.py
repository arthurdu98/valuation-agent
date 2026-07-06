import os
import logging
from typing import Any
from pydantic import BaseModel as PydanticBaseModel
from src.backend.agents.llm.config import load_llm_config, ModelConfig
from src.backend.agents.llm.fallback import LLMFallbackRunner
from src.backend.agents.llm.usage import UsageTracker

logger = logging.getLogger(__name__)


class LLMRouter:
    """Routes LLM calls to appropriate models based on role configuration."""

    def __init__(self, config_path: str = "configs/llm.yaml"):
        self._config = load_llm_config(config_path)
        self._usage = UsageTracker()
        self._fallback = LLMFallbackRunner(self._config.fallback_chain)
        self._models_cache: dict[str, Any] = {}
        logger.info(f"LLMRouter initialized with {len(self._config.models)} models")

    def _get_api_key(self, model_config: ModelConfig) -> str:
        if not model_config.api_key_env:
            return ""
        return os.environ.get(model_config.api_key_env, "")

    def _create_chat_model(self, model_name: str):
        """Create a LangChain ChatModel instance for the given model name."""
        if model_name in self._models_cache:
            return self._models_cache[model_name]

        config = self._config.models.get(model_name)
        if not config:
            raise ValueError(f"Model '{model_name}' not found in config")

        api_key = self._get_api_key(config)

        if config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            model = ChatAnthropic(
                model=config.model_name,
                api_key=api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif config.provider == "openai":
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model=config.model_name,
                api_key=api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif config.provider == "openai_compatible":
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model=config.model_name,
                api_key=api_key or "not-needed",
                base_url=config.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif config.provider == "ollama":
            from langchain_community.chat_models import ChatOllama
            model = ChatOllama(
                model=config.model_name,
                base_url=config.base_url or "http://localhost:11434",
                temperature=config.temperature,
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

        self._models_cache[model_name] = model
        return model

    def get_model(self, role: str):
        """Get the ChatModel assigned to a role."""
        model_name = self._config.role_routing.get(role, self._config.default_model)
        return self._create_chat_model(model_name)

    def get_model_name_for_role(self, role: str) -> str:
        """Get the model name string for a role."""
        return self._config.role_routing.get(role, self._config.default_model)

    def call(
        self,
        role: str,
        prompt: str,
        pydantic_model: type[PydanticBaseModel] | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> str | PydanticBaseModel:
        """Call LLM with role-based routing and fallback.

        Args:
            role: The agent role (e.g., "master_narrate", "debate_judge")
            prompt: The prompt to send
            max_retries: Number of retries per model
            retry_delay: Base delay between retries (exponential backoff)

        Returns:
            The LLM response text.
        """
        primary_model_name = self.get_model_name_for_role(role)

        def invoke(model_name: str):
            model = self._create_chat_model(model_name)
            if pydantic_model is not None and hasattr(model, "with_structured_output"):
                return model.with_structured_output(pydantic_model).invoke(prompt)
            return model.invoke(prompt)

        model_name, response, latency = self._fallback.run(
            primary_model_name,
            invoke,
            role=role,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        content = response.content if hasattr(response, "content") else str(response)
        config = self._config.models[model_name]
        self._usage.record(
            model=model_name,
            role=role,
            prompt=prompt,
            response=content,
            latency_ms=latency,
            input_cost_per_1k=config.cost_per_1k_input,
            output_cost_per_1k=config.cost_per_1k_output,
        )
        logger.info("[%s] %s responded in %.0fms", role, model_name, latency)
        return response if pydantic_model is not None else content

    def get_usage_stats(self) -> dict:
        """Get aggregated usage statistics."""
        return self._usage.get_usage_stats()
