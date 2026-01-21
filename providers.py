import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        pass

class DuckDuckGoSearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        if not DDGS:
            logger.warning("duckduckgo-search not installed. Returning empty results.")
            return []
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
                return [
                    {
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "snippet": r.get("body", "")
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

class MockSearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        return [
            {
                "title": f"关于 {query} 的搜索结果",
                "link": "http://example.com",
                "snippet": f"这是关于 {query} 的模拟搜索结果。在真实环境中，这里会显示来自搜索引擎的摘要信息。"
            }
        ]

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        pass

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-3.5-turbo"):
        if not OpenAI:
            raise ImportError("openai package is not installed")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""

    def generate_json(self, prompt: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        # Append JSON instruction if not present
        if "json" not in prompt.lower():
            prompt += "\n\nPlease respond with valid JSON."
            
        content = self.generate(prompt, system_prompt="You are a helpful assistant that outputs JSON.")
        
        # Simple cleanup to handle markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM response: {content}")
            return {}

class MockLLMProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        return "这是模拟的 LLM 回复。请配置有效的 LLM API Key 以获得真实分析。"

    def generate_json(self, prompt: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        # Return a structure that mimics what we expect for creative generation
        # This is a fallback if LLM is not configured
        return {
            "summary": "这是模拟的热点分析摘要。",
            "timeline": ["2026年1月1日: 事件开始", "2026年1月2日: 事件发酵"],
            "creatives": [
                {
                    "name": "模拟创意产品",
                    "features": ["功能点1", "功能点2"],
                    "target_users": "模拟目标用户",
                    "scores": {"interest": 85, "usefulness": 75, "total": 83},
                    "quality": "优秀",
                    "quality_class": "excellent",
                    "justification": {"interest": "模拟评分理由", "usefulness": "模拟评分理由"}
                }
            ]
        }

def get_search_provider(config) -> SearchProvider:
    if config.SEARCH_PROVIDER == "duckduckgo":
        return DuckDuckGoSearchProvider()
    return MockSearchProvider()

def get_llm_provider(config) -> LLMProvider:
    if config.LLM_API_KEY:
        return OpenAILLMProvider(
            api_key=config.LLM_API_KEY, 
            base_url=config.LLM_BASE_URL,
            model=config.LLM_MODEL
        )
    return MockLLMProvider()
