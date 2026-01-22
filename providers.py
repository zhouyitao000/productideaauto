import json
import logging
import requests
import re
from urllib.parse import quote
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

class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://google.serper.dev/search"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        if not self.api_key:
            logger.warning("Serper API key not configured.")
            return []
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "q": query,
            "num": limit,
            "gl": "cn",
            "hl": "zh-cn"
        })
        
        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()
            results = response.json().get("organic", [])
            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", "")
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []

class BaiduSearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        # Basic scraper for Baidu - Note: Baidu often blocks scrapers
        url = f"https://www.baidu.com/s?wd={quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Simple regex extraction (brittle but no extra deps)
            # Extracting title and url patterns from Baidu's HTML structure
            content = response.text
            results = []
            
            # This is a very simplified regex and might break if Baidu changes HTML
            # Looking for result containers
            # <h3 class="t"><a href="...">Title</a></h3>
            
            # Use a simple approach: Split by result container if possible, or just regex findall
            # Regex for standard result link
            matches = re.finditer(r'<h3[^>]*>[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>[\s\S]*?</h3>', content)
            
            for match in matches:
                if len(results) >= limit:
                    break
                link = match.group(1)
                title_raw = match.group(2)
                # Remove HTML tags from title
                title = re.sub(r'<[^>]+>', '', title_raw).strip()
                
                # Baidu links are redirects, but we use them as is
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": "Baidu Search Result" # Snippet extraction is harder with regex
                })
                
            return results
        except Exception as e:
            logger.error(f"Baidu search failed: {e}")
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
    provider_type = config.SEARCH_PROVIDER.lower()
    
    if provider_type == "duckduckgo":
        return DuckDuckGoSearchProvider()
    elif provider_type == "google" or provider_type == "serper":
        return SerperSearchProvider(config.SERPER_API_KEY)
    elif provider_type == "baidu":
        return BaiduSearchProvider()
        
    return MockSearchProvider()

def get_llm_provider(config) -> LLMProvider:
    if config.LLM_API_KEY:
        return OpenAILLMProvider(
            api_key=config.LLM_API_KEY, 
            base_url=config.LLM_BASE_URL,
            model=config.LLM_MODEL
        )
    return MockLLMProvider()
