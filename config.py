import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Weibo API
    TIANAPI_KEY = os.getenv("TIANAPI_KEY", "6e333e2407e88821ce16a6a8cba513e8")
    WEIBO_API_URL = "https://apis.tianapi.com/weibohot/index"
    DOUYIN_API_URL = "https://apis.tianapi.com/douyinhot/index"
    
    # LLM Configuration
    # Use DeepSeek by default as requested
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    
    # Search Configuration
    # Options: "duckduckgo", "google" (requires SERPER_API_KEY), "baidu"
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    # App Settings
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", ".")
    MAX_TOPICS = int(os.getenv("MAX_TOPICS", "10"))
    CONCURRENCY = int(os.getenv("CONCURRENCY", "3"))
