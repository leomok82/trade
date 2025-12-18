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
    
class MovingAverageCrossover(Strategy):
    def __init__(self, short_window=50, long_window=200):
        super().__init__()
        self.short_window = short_window
        self.long_window = long_window
        self.history = defaultdict(list)

    def on_bar(self, symbol, bar):
        self.history[symbol].append(bar['close'])
        
        if len(self.history[symbol]) < self.long_window:
            return 0

        short_ma = sum(self.history[symbol][-self.short_window:]) / self.short_window
        long_ma = sum(self.history[symbol][-self.long_window:]) / self.long_window

        if short_ma > long_ma:
            return 1
        elif short_ma < long_ma:
            return -1
        
        return 0

class BuyLow(Strategy):
    def __init__(self, factor: tuple = (3, 2), stop_loss : float = 3, timeframe_minutes: int = 390,
                 use_regime: bool = True, regime_adjust: bool = True,
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
            regime_adjust: Adjust thresholds based on regime (default: True)
                - LOW regime: Tighter thresholds (more sensitive)
                - HIGH/EXTREME regime: Wider thresholds or skip trading
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
        self.history = defaultdict(list)
        self.factor = factor  # (entry_std_devs, exit_std_devs)
        self.entry_price = defaultdict(lambda: 1e8)
        self.pos = defaultdict(int)
        self.day_high = defaultdict(float)
        self.entry_std = defaultdict(float)
        self.stop_loss = stop_loss
        self.timeframe_minutes = timeframe_minutes
        
        # Regime detection
        self.use_regime = use_regime
        self.regime_adjust = regime_adjust
        self.regime_detector = RegimeDetector(lookback_window=timeframe_minutes, regime_window=20) if use_regime else None
        self.current_regime = defaultdict(lambda: VolatilityRegime.NORMAL)
        
        # Trend detection
        self.use_trend = use_trend
        self.trend_detector = TrendDetector(lookback = 60) if use_trend else None
        self.current_trend = defaultdict(lambda: TrendDirection.FLAT)
        
        self.cooldown = defaultdict(int)
        self.cooldown_period = 30

    def on_bar(self, symbol, bar):
        self.history[symbol].append(bar['close'])
        
        # Need at least timeframe_minutes bars to calculate meaningful statistics
        if len(self.history[symbol]) <= self.timeframe_minutes:
            return 0
        
        # Update regime detector if enabled (pass history, don't let it store)
        if self.use_regime and self.regime_detector:
            regime = self.regime_detector.calculate(symbol, self.history[symbol])
            self.current_regime[symbol] = regime
        
        # Update trend detector if enabled (pass history, don't let it store)
        if self.use_trend and self.trend_detector:
            trend = self.trend_detector.calculate(symbol, self.history[symbol])
            self.current_trend[symbol] = trend
        
        # Get price history for the specified timeframe (excluding current)
        lookback_prices = np.array(self.history[symbol][-self.timeframe_minutes-1:-1])
        current_price = self.history[symbol][-1]
        
        # Calculate statistical measures
        mean_price = np.mean(lookback_prices)
        std_dev = np.std(lookback_prices)
        
        # Avoid division by zero
        if std_dev < 1e-6:
            return 0
        
        # Calculate z-score (how many standard deviations from mean)
        z_score = (current_price - mean_price) / std_dev
        
        # Adjust thresholds based on volatility regime
        entry_threshold = self.factor[0]
        exit_threshold = self.factor[1]
        stop_loss_threshold = self.stop_loss
        
        if self.regime_adjust and self.use_regime:
            regime = self.current_regime[symbol]
            
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
                if self.pos[symbol] == 0:
                    return 0  
                exit_threshold *= 1.5
                stop_loss_threshold *= 1.5
        
        # tick cooldown
        self.cooldown[symbol] -= 1

        # Stop Loss: Exit if price drops stop_loss_threshold std devs below entry
        if self.pos[symbol] == 1:
            price_change_std = (current_price - self.entry_price[symbol]) / self.entry_std[symbol]
            
            if price_change_std < -stop_loss_threshold:  # Dropped too much (stop loss)
                self.pos[symbol] = 0
                return -1
        # Take Profit: Exit if price rises exit_threshold std devs above entry
        if self.pos[symbol] == 1:
            price_change_std = (current_price - self.entry_price[symbol]) / self.entry_std[symbol]
            
            if price_change_std > exit_threshold:  # Recovered enough (take profit)
                self.pos[symbol] = 0
                return -1

        # Trend Filter
        if self.use_trend:
            trend = self.current_trend[symbol]
            if trend == TrendDirection.DOWN:
                return 0

        
        # Entry when z-score < -entry_threshold and trend is favorable
        if self.pos[symbol] == 0 and z_score < -entry_threshold and self.cooldown[symbol]<=0:
            self.pos[symbol] = 1
            self.entry_price[symbol] = current_price
            self.entry_std[symbol] = std_dev  # Store std dev at entry for exit calculations
            self.cooldown[symbol] = self.cooldown_period
            return 1
        
        


        return 0
