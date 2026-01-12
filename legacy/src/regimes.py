import numpy as np
from collections import defaultdict
from enum import Enum

class VolatilityRegime(Enum):
    """Volatility regime classifications"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"

class RegimeDetector:
    """
    Detects volatility regimes based on rolling standard deviation of returns.
    
    Uses percentile-based thresholds to classify current volatility:
    - LOW: Below 25th percentile
    - NORMAL: Between 25th and 75th percentile
    - HIGH: Between 75th and 90th percentile
    - EXTREME: Above 90th percentile
    
    Note: This class does NOT store price history. Pass history from strategy.
    """
    
    def __init__(self, lookback_window: int = 390, regime_window: int = 60):
        """
        Initialize regime detector.
        
        Args:
            lookback_window: Number of bars to calculate historical volatility distribution (default: 390 = 1 day)
            regime_window: Number of bars to calculate current volatility (default: 20 = 20 minutes)
        """
        self.lookback_window = lookback_window
        self.regime_window = regime_window
        
    def calculate(self, price_history: list) -> VolatilityRegime:
        """
        Calculate volatility regime from provided price history.
        
        Args:
            price_history: List of historical prices (from strategy)
            
        Returns:
            Current volatility regime for the symbol
        """
        # Need enough data to calculate volatility
        if len(price_history) < self.regime_window + 1:
            return VolatilityRegime.NORMAL
        
        # Calculate returns for regime window
        prices = np.array(price_history[-self.regime_window-1:])
        returns = np.diff(prices) / prices[:-1]
        
        # Current volatility (annualized standard deviation of returns)
        # Assuming minute bars: sqrt(252 * 390) to annualize
        current_vol = np.std(returns) * np.sqrt(252 * 390)
        
        # Need lookback window to establish regime thresholds
        if len(price_history) < self.lookback_window:
            return VolatilityRegime.NORMAL
        
        # Calculate historical volatility distribution using vectorized operations
        lookback_prices = np.array(price_history[-self.lookback_window:])
        
        # Calculate all returns at once
        all_returns = np.diff(lookback_prices) / lookback_prices[:-1]
        
        # Use rolling window std calculation (more efficient)
        # Calculate rolling std using pandas for efficiency
        import pandas as pd
        returns_series = pd.Series(all_returns)
        rolling_std = returns_series.rolling(window=self.regime_window).std()
        historical_vols = rolling_std.dropna().values * np.sqrt(252 * 390)
        
        # Calculate percentile thresholds
        p25 = np.percentile(historical_vols, 25)
        p75 = np.percentile(historical_vols, 75)
        p90 = np.percentile(historical_vols, 90)
        
        # Calculate current percentile
        percentile = (historical_vols < current_vol).sum() / len(historical_vols) * 100
        
        # Classify regime
        if current_vol < p25:
            regime = VolatilityRegime.LOW
        elif current_vol < p75:
            regime = VolatilityRegime.NORMAL
        elif current_vol < p90:
            regime = VolatilityRegime.HIGH
        else:
            regime = VolatilityRegime.EXTREME
        
        return regime
    


    
    def _get_regime_description(self, regime: VolatilityRegime) -> str:
        """Get human-readable description of regime."""
        descriptions = {
            VolatilityRegime.LOW: "Low volatility - Market is calm, tight ranges",
            VolatilityRegime.NORMAL: "Normal volatility - Typical market conditions",
            VolatilityRegime.HIGH: "High volatility - Increased price swings",
            VolatilityRegime.EXTREME: "Extreme volatility - Significant market stress"
        }
        return descriptions.get(regime, "Unknown regime")


# Made with Bob
