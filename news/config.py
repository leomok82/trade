import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
TARGET_SYMBOL = "SPY"
