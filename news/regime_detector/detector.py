from enum import Enum
from typing import List, Dict

class MarketRegime(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class RegimeDetector:
    def __init__(self, lookback_period: int = 20):
        self.lookback_period = lookback_period

    def detect_regime(self, market_data: List[Dict]) -> MarketRegime:
        """
        Analyzes historical data to determine the current regime.
        This effectively acts as a pure function on the data.
        """
        if len(market_data) < self.lookback_period:
            return MarketRegime.UNKNOWN
        
        # Simple implementation: Compare current price to SMA
        # Assuming market_data is sorted by time ascending (latest last)
        
        # Extract closing prices
        try:
            prices = [d['close'] for d in market_data]
            current_price = prices[-1]
            
            # Calculate SMA
            recent_prices = prices[-self.lookback_period:]
            sma = sum(recent_prices) / len(recent_prices)
            
            # Determine Regime
            # If price > SMA by 1%, Bullish
            # If price < SMA by 1%, Bearish
            # Otherwise Neutral
            
            threshold = 0.01 # 1%
            
            if current_price > sma * (1 + threshold):
                return MarketRegime.BULLISH
            elif current_price < sma * (1 - threshold):
                return MarketRegime.BEARISH
            else:
                return MarketRegime.NEUTRAL
                
        except KeyError:
            # Handle case where 'close' key is missing
            return MarketRegime.UNKNOWN
