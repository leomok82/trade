import sys
import os

# Add the current directory to sys.path to ensure modules can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, TARGET_SYMBOL
from data_retrieval.alpaca_client import AlpacaDataProvider
from regime_detector.detector import RegimeDetector

def main():
    print("Starting News Trading System Component...")

    # 1. Validation
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        print("Error: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env or environment.")
        return

    # 2. Initialization
    data_provider = AlpacaDataProvider(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
    detector = RegimeDetector(lookback_period=20)

    try:
        # 3. Execution
        print(f"Fetching data for {TARGET_SYMBOL}...")
        bars = data_provider.get_historical_data(TARGET_SYMBOL, limit=50)
        
        if not bars:
            print("No data fetched. Exiting.")
            return

        print(f"Retrieved {len(bars)} bars.")
        
        print(f"Analyzing regime...")
        current_regime = detector.detect_regime(bars)
        
        print(f"Detected Regime: {current_regime.value.upper()}")

    except Exception as e:
        print(f"An error occurred during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
