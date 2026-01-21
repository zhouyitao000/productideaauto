import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Weibo API
    TIANAPI_KEY = os.getenv("TIANAPI_KEY", "6e333e2407e88821ce16a6a8cba513e8")
    
    # LLM Configuration
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    # Search Configuration
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    # App Settings
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", ".")
    MAX_TOPICS = int(os.getenv("MAX_TOPICS", "5"))
    CONCURRENCY = int(os.getenv("CONCURRENCY", "3"))
