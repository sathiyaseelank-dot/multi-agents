"""API-based agents for OpenRouter, Groq, Google AI, and other providers.

These agents call APIs directly instead of using CLI tools.
Used as fallback when CLI agents are slow or unavailable.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import aiohttp

from .base_agent import AgentConfig, BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# API Provider configurations
PROVIDER_CONFIGS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "auth_header": "Authorization",
        "models": [
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.3-70b-instruct",
            "mistralai/mistral-large",
            "qwen/qwen-2.5-coder-32b-instruct",
        ],
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "auth_header": "Authorization",
        "models": [
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    },
    "google_ai": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "auth_header": "Content-Type",
        "models": ["gemini-2.0-flash", "gemini-1.5-flash"],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "auth_header": "Authorization",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
}

# System prompt for code generation tasks
CODE_GENERATION_SYSTEM = """You are an expert software developer. Generate clean, working code.

Rules:
- Write complete, functional code
- Include necessary imports
- Follow best practices
- Add brief comments where helpful
- Return ONLY code, no explanations
- Use appropriate file extensions"""

# System prompt for planning tasks
PLANNING_SYSTEM = """You are a task planner. Break down requests into actionable steps.

Return JSON only with this structure:
{
  "epic": "task description",
  "tasks": [
    {
      "id": "task-001",
      "agent": "backend|frontend|testing",
      "title": "short title",
      "description": "what to build",
      "dependencies": []
    }
  ]
}"""


class APIAgent(BaseAgent):
    """Base class for API-based agents."""
    
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        role: str = "backend",
        name: Optional[str] = None,
        timeout: int = 120,
    ):
        """Initialize API agent.
        
        Args:
            provider: Provider name (openrouter, groq, google_ai, etc.)
            api_key: API key for authentication
            model: Model name to use
            role: Agent role (backend, frontend, testing, planner)
            name: Custom agent name (default: {provider}_{role})
            timeout: Request timeout in seconds
        """
        if name is None:
            name = f"{provider}_{role}"
        
        config = AgentConfig(
            name=name,
            role=role,
            command="",  # No CLI command, uses API
            timeout_seconds=timeout,
            retry_count=2,
            env_vars={"API_KEY": api_key},
        )
        
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.provider_config = PROVIDER_CONFIGS.get(provider, {})
        self.name = name  # Store the name attribute
        self.role = role  # Store the role attribute
        
        super().__init__(config)

    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        """Build the full prompt to send to the API.
        
        Args:
            task_description: The main task description
            context: Optional context from previous tasks
            
        Returns:
            Formatted prompt string
        """
        prompt = task_description
        
        if context:
            prompt += "\n\nContext from previous tasks:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
        
        return prompt

    async def _run(self, prompt: str) -> AgentResult:
        """Execute API call."""
        import time
        start_time = time.monotonic()
        
        try:
            # Determine system prompt based on role
            if self.role == "planner":
                system_prompt = PLANNING_SYSTEM
            else:
                system_prompt = CODE_GENERATION_SYSTEM
            
            # Build request
            if self.provider == "google_ai":
                # Google AI has different format
                url = self.provider_config["base_url"].format(model=self.model)
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 4096,
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                }
                params = {"key": self.api_key}
            else:
                # OpenAI-compatible format (OpenRouter, Groq, DeepSeek)
                url = self.provider_config["base_url"]
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                params = {}
            
            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        return AgentResult(
                            agent=self.name,
                            status="error",
                            raw_output=json.dumps(result),
                            error=f"API error {response.status}: {result}",
                            execution_time=time.monotonic() - start_time,
                        )
                    
                    # Extract response
                    if self.provider == "google_ai":
                        content = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    else:
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    return AgentResult(
                        agent=self.name,
                        status="success",
                        raw_output=content,
                        parsed_output=self.parse_output(content),
                        execution_time=time.monotonic() - start_time,
                    )
        
        except asyncio.TimeoutError:
            return AgentResult(
                agent=self.name,
                status="timeout",
                error=f"API call timed out after {self.config.timeout_seconds}s",
                execution_time=time.monotonic() - start_time,
            )
        except Exception as e:
            return AgentResult(
                agent=self.name,
                status="error",
                error=str(e),
                execution_time=time.monotonic() - start_time,
            )
    
    def parse_output(self, raw_output: str) -> Any:
        """Parse API output."""
        # Try to extract JSON for planner role
        if self.role == "planner":
            import re
            # Look for JSON in the response
            match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return raw_output
        
        # For code generation, extract code blocks
        import re
        code_match = re.search(r'```(?:\w+)?\n(.*?)```', raw_output, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        return raw_output
    
    def is_available(self) -> bool:
        """Check if API agent is available."""
        return bool(self.api_key) and bool(self.model)


def load_api_keys() -> dict:
    """Load API keys from config file."""
    project_root = Path(__file__).resolve().parent.parent
    keys_file = project_root / "config" / "api_keys.json"
    if keys_file.exists():
        try:
            return json.loads(keys_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def create_api_agent(
    provider: str,
    api_key: str,
    model: str,
    role: str = "backend",
    name: Optional[str] = None,
) -> Optional[APIAgent]:
    """Create an API agent for the specified provider.
    
    Args:
        provider: Provider name (openrouter, groq, google_ai, deepseek)
        api_key: API key
        model: Model name
        role: Agent role
        name: Custom name
    
    Returns:
        APIAgent instance or None if provider not supported
    """
    if provider not in PROVIDER_CONFIGS:
        logger.warning(f"Unknown provider: {provider}")
        return None
    
    return APIAgent(
        provider=provider,
        api_key=api_key,
        model=model,
        role=role,
        name=name,
    )


def get_available_models(provider: str) -> list[str]:
    """Get available models for a provider."""
    config = PROVIDER_CONFIGS.get(provider)
    if config:
        return config.get("models", [])
    return []
