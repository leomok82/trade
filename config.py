import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ALPACA_KEY = os.getenv("ALPACA_KEY")
    ALPACA_SECRET = os.getenv("ALPACA_SECRET")
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    # Add Webull credentials if needed, or other config here
    WEBULL_USERNAME = os.getenv("WEBULL_USERNAME")
    WEBULL_PASSWORD = os.getenv("WEBULL_PASSWORD")
