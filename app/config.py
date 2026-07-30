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
# Many corporate sites (Cloudflare, Akamai) 403 non-browser UAs. Since we're
# only fetching pages a normal researcher would open in a browser, present
# ourselves as one. Adjust here if you want to identify as a bot instead.
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
