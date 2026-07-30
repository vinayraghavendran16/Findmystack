import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./findmystack.db")

VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "claude-sonnet-5")
HTTP_TIMEOUT = 20.0
HTTP_USER_AGENT = "FindmystackBot/0.1 (+https://github.com/vinayraghavendran16/findmystack)"
