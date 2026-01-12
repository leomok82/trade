import numpy as np
from abc import ABC, abstractmethod
from collections import defaultdict
from .regimes import RegimeDetector, VolatilityRegime
from .trends import TrendDetector, TrendDirection

class Strategy(ABC):
    def __init__(self):
        self.pos = defaultdict(int)

    @abstractmethod
    def on_bar(self, symbol, bar):
        """
        Called when a new bar is available.
        Should return a signal: 1 (buy), -1 (sell), 0 (hold).
        """
        pass




class BuyLow(Strategy):
    def __init__(self, factor: tuple = (3, 2), stop_loss : float = 3, timeframe_minutes: int = 390,
                 use_regime: bool = True,
                 use_trend: bool = True):
        """
        Variance-based strategy that buys on significant price drops and sells on recoveries.
        Now with volatility regime awareness and trend filtering for adaptive risk management.
        
        Args:
            factor: tuple of (entry_threshold, exit_threshold) in standard deviations
                - entry_threshold: How many std devs below mean to trigger buy (default: 3)
                - exit_threshold: How many std devs from entry to trigger sell/stop (default: 2)
            stop_loss: How many std devs below entry to trigger stop loss (default: 3)
            timeframe_minutes: Lookback period in minutes for calculating statistics (default: 390 = 1 trading day)
                - 390 = 1 day (6.5 hours)
                - 780 = 2 days
                - 60 = 1 hour
                - 30 = 30 minutes
            use_regime: Enable volatility regime detection (default: True)

            use_trend: Enable trend detection (default: True)
            allow_flat_trend: Allow trading in flat/sideways markets (default: True)
                - If True: Trade in UP and FLAT trends
                - If False: Only trade in UP trends
        
        Logic:
            - Calculate rolling variance and standard deviation of prices over specified timeframe
            - Detect volatility regime (LOW, NORMAL, HIGH, EXTREME)
            - Detect trend direction (UP, FLAT, DOWN)
            - Only enter trades when trend is UP or FLAT (if allowed)
            - Adjust entry/exit thresholds based on regime if enabled
            - Buy when price drops below (mean - entry_threshold * std_dev)
            - Stop loss when price drops stop_loss * std_dev below entry
            - Take profit when price rises exit_threshold * std_dev above entry
        """
        super().__init__()

        self.factor = factor  # (entry_std_devs, exit_std_devs)
        self.stop_loss = stop_loss
        self.timeframe_minutes = timeframe_minutes
        
        # Regime detection
        self.use_regime = use_regime
        self.regime_detector = RegimeDetector(lookback_window=timeframe_minutes, regime_window=20) if use_regime else None
        
        # Trend detection
        self.use_trend = use_trend
        self.trend_detector = TrendDetector(lookback = 300) if use_trend else None
        self.cooldown_period = 30

    def on_bar(self, bar ,st ):
        st.history.append(bar['close'])
        
        # Need at least timeframe_minutes bars to calculate meaningful statistics
        if len(st.history) <= self.timeframe_minutes:
            return 0
        
        # Update regime detector if enabled (pass history, don't let it store)
        if self.use_regime and self.regime_detector:
            regime = self.regime_detector.calculate(st.history)
        
        # Update trend detector if enabled (pass history, don't let it store)
        if self.use_trend and self.trend_detector:
            trend = self.trend_detector.calculate(st.history)
        
        # Get price history for the specified timeframe (excluding current)
        lookback_prices = np.array(st.history[-self.timeframe_minutes-1:-1])
        current_price = st.history[-1]
        
        # Calculate statistical measures
        mean_price = st.entry_mean if st.entry_mean > 0 else np.mean(lookback_prices)
        
        std_dev =  st.entry_std if st.entry_std > 0 else np.std(lookback_prices)
        
        # Avoid division by zero
        if std_dev < 1e-6:
            return 0
        
        # Calculate z-score (how many standard deviations from mean)
        z_score = (current_price - mean_price) / std_dev

        
        # Adjust thresholds based on volatility regime
        entry_threshold = self.factor[0]
        exit_threshold = self.factor[1]
        stop_loss_threshold = self.stop_loss
        
        if  self.use_regime:            
            if regime == VolatilityRegime.LOW:
                # In low volatility, use tighter thresholds (more sensitive)
                entry_threshold *= 0.7
                exit_threshold *= 0.8
                stop_loss_threshold *= 0.8
            elif regime == VolatilityRegime.HIGH:
                # In high volatility, use wider thresholds (less sensitive)
                entry_threshold *= 1.3
                exit_threshold *= 1.2
                stop_loss_threshold *= 1.2
            elif regime == VolatilityRegime.EXTREME:
                # In extreme volatility, avoid new entries or use very wide thresholds
                if st.pos == 0:
                    return 0  
                exit_threshold *= 1.5
                stop_loss_threshold *= 1.5
        
        # tick cooldown
        if st.cooldown>0:
            st.cooldown -= 1

        # Stop Loss: Exit if price drops stop_loss_threshold std devs below entry
        if st.pos == 1:
            price_change_std = (current_price - mean_price) / std_dev
            st.cooldown = self.cooldown_period

            if price_change_std < -stop_loss_threshold:  # Dropped too much (stop loss)
                st.pos = 0
                return -1
            
            if price_change_std > exit_threshold:  # Recovered enough (take profit)
                st.pos = 0
                return -1

        # Trend Filter
        if self.use_trend:
            if trend == TrendDirection.DOWN:
                return 0

        
        # Entry when z-score < -entry_threshold and trend is favorable
        if st.pos == 0 and z_score < -entry_threshold and st.cooldown <= 0:
            st.pos = 1
            st.entry_price = current_price
            st.entry_std = np.std(lookback_prices)
            st.entry_mean = np.mean(lookback_prices)
            return 1

        return 0
