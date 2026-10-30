import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
POLL_SECONDS = max(60, int(os.getenv("POLL_SECONDS", "120")))
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "10000"))
DB_PATH = os.getenv("DB_PATH", "solana_research.sqlite3")
