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
    """
    
    def __init__(self, lookback_window: int = 390, regime_window: int = 20):
        """
        Initialize regime detector.
        
        Args:
            lookback_window: Number of bars to calculate historical volatility distribution (default: 390 = 1 day)
            regime_window: Number of bars to calculate current volatility (default: 20 = 20 minutes)
        """
        self.lookback_window = lookback_window
        self.regime_window = regime_window
        self.history = defaultdict(list)
        self.current_regime = defaultdict(lambda: VolatilityRegime.NORMAL)
        self.current_volatility = defaultdict(float)
        self.volatility_percentile = defaultdict(float)
        
    def on_bar(self, symbol: str, bar: dict) -> VolatilityRegime:
        """
        Process a new bar and update volatility regime.
        
        Args:
            symbol: Trading symbol
            bar: Dictionary containing at least 'close' price
            
        Returns:
            Current volatility regime for the symbol
        """
        # Store price history
        self.history[symbol].append(bar['close'])
        
        # Need enough data to calculate volatility
        if len(self.history[symbol]) < self.regime_window + 1:
            return VolatilityRegime.NORMAL
        
        # Calculate returns for regime window
        prices = np.array(self.history[symbol][-self.regime_window-1:])
        returns = np.diff(prices) / prices[:-1]
        
        # Current volatility (annualized standard deviation of returns)
        # Assuming minute bars: sqrt(252 * 390) to annualize
        current_vol = np.std(returns) * np.sqrt(252 * 390)
        self.current_volatility[symbol] = current_vol
        
        # Need lookback window to establish regime thresholds
        if len(self.history[symbol]) < self.lookback_window:
            return VolatilityRegime.NORMAL
        
        # Calculate historical volatility distribution using vectorized operations
        lookback_prices = np.array(self.history[symbol][-self.lookback_window:])
        
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
        self.volatility_percentile[symbol] = percentile
        
        # Classify regime
        if current_vol < p25:
            regime = VolatilityRegime.LOW
        elif current_vol < p75:
            regime = VolatilityRegime.NORMAL
        elif current_vol < p90:
            regime = VolatilityRegime.HIGH
        else:
            regime = VolatilityRegime.EXTREME
        
        self.current_regime[symbol] = regime
        return regime
    
    def get_regime(self, symbol: str) -> VolatilityRegime:
        """Get current regime for a symbol."""
        return self.current_regime[symbol]
    
    def get_volatility(self, symbol: str) -> float:
        """Get current annualized volatility for a symbol."""
        return self.current_volatility[symbol]
    
    def get_percentile(self, symbol: str) -> float:
        """Get current volatility percentile (0-100) for a symbol."""
        return self.volatility_percentile[symbol]
    
    def get_regime_stats(self, symbol: str) -> dict:
        """
        Get comprehensive regime statistics for a symbol.
        
        Returns:
            Dictionary with regime, volatility, and percentile information
        """
        return {
            'regime': self.current_regime[symbol].value,
            'volatility': self.current_volatility[symbol],
            'percentile': self.volatility_percentile[symbol],
            'description': self._get_regime_description(self.current_regime[symbol])
        }
    
    def _get_regime_description(self, regime: VolatilityRegime) -> str:
        """Get human-readable description of regime."""
        descriptions = {
            VolatilityRegime.LOW: "Low volatility - Market is calm, tight ranges",
            VolatilityRegime.NORMAL: "Normal volatility - Typical market conditions",
            VolatilityRegime.HIGH: "High volatility - Increased price swings",
            VolatilityRegime.EXTREME: "Extreme volatility - Significant market stress"
        }
        return descriptions.get(regime, "Unknown regime")


class AdaptiveRegimeDetector(RegimeDetector):
    """
    Enhanced regime detector that adapts thresholds based on recent market behavior.
    Uses exponential moving average of volatility for smoother regime transitions.
    """
    
    def __init__(self, lookback_window: int = 390, regime_window: int = 20, smoothing: float = 0.1):
        """
        Initialize adaptive regime detector.
        
        Args:
            lookback_window: Number of bars for historical distribution
            regime_window: Number of bars for current volatility calculation
            smoothing: EMA smoothing factor (0-1), lower = more smoothing
        """
        super().__init__(lookback_window, regime_window)
        self.smoothing = smoothing
        self.ema_volatility = defaultdict(float)
        
    def on_bar(self, symbol: str, bar: dict) -> VolatilityRegime:
        """Process bar with EMA smoothing of volatility."""
        # Get base regime calculation
        regime = super().on_bar(symbol, bar)
        
        # Apply EMA smoothing to volatility
        current_vol = self.current_volatility[symbol]
        if self.ema_volatility[symbol] == 0:
            self.ema_volatility[symbol] = current_vol
        else:
            self.ema_volatility[symbol] = (
                self.smoothing * current_vol + 
                (1 - self.smoothing) * self.ema_volatility[symbol]
            )
        
        # Reclassify using smoothed volatility
        if len(self.history[symbol]) >= self.lookback_window:
            smoothed_vol = self.ema_volatility[symbol]
            
            # Recalculate thresholds using vectorized operations
            lookback_prices = np.array(self.history[symbol][-self.lookback_window:])
            all_returns = np.diff(lookback_prices) / lookback_prices[:-1]
            
            import pandas as pd
            returns_series = pd.Series(all_returns)
            rolling_std = returns_series.rolling(window=self.regime_window).std()
            historical_vols = rolling_std.dropna().values * np.sqrt(252 * 390)
            
            p25 = np.percentile(historical_vols, 25)
            p75 = np.percentile(historical_vols, 75)
            p90 = np.percentile(historical_vols, 90)
            
            # Classify using smoothed volatility
            if smoothed_vol < p25:
                regime = VolatilityRegime.LOW
            elif smoothed_vol < p75:
                regime = VolatilityRegime.NORMAL
            elif smoothed_vol < p90:
                regime = VolatilityRegime.HIGH
            else:
                regime = VolatilityRegime.EXTREME
            
            self.current_regime[symbol] = regime
        
        return regime
    
    def get_smoothed_volatility(self, symbol: str) -> float:
        """Get EMA-smoothed volatility."""
        return self.ema_volatility[symbol]

# Made with Bob
