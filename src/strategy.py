import numpy as np
from abc import ABC, abstractmethod
from collections import defaultdict

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
    def __init__(self, factor: tuple = (3, 2), stop_loss = 3):
        """
        Variance-based strategy that buys on significant price drops and sells on recoveries.
        
        Args:
            factor: tuple of (entry_threshold, exit_threshold) in standard deviations
                - entry_threshold: How many std devs below mean to trigger buy (default: 2.0)
                - exit_threshold: How many std devs from entry to trigger sell/stop (default: 1.5)
        
        Logic:
            - Calculate rolling variance and standard deviation of prices
            - Buy when price drops below (mean - entry_threshold * std_dev)
            - Stop loss when price drops exit_threshold * std_dev below entry
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
       

    def on_bar(self, symbol, bar):
        self.history[symbol].append(bar['close'])
        
        # Need at least 390 bars (1 trading day) to calculate meaningful statistics
        if len(self.history[symbol]) <= 390:
            return 0
        
        # Get intraday price history (last 6.5 hours = 390 minutes)
        intraday_prices = np.array(self.history[symbol][-int(60*6.5):])
        current_price = self.history[symbol][-1]
        
        # Calculate statistical measures
        mean_price = np.mean(intraday_prices)
        std_dev = np.std(intraday_prices)
        
        # Avoid division by zero
        if std_dev < 1e-6:
            return 0
        
        # Calculate z-score (how many standard deviations from mean)
        z_score = (current_price - mean_price) / std_dev
        
        # Stop Loss: Exit if price drops exit_threshold std devs below entry
        if self.pos[symbol] == 1:
            price_change_std = (current_price - self.entry_price[symbol]) / self.entry_std[symbol]
            
            if price_change_std < -self.stop_loss:  # Dropped too much (stop loss)
                self.pos[symbol] = 0
                return -1

        # Buy Signal: Price is significantly below mean (oversold condition)
        # Entry when z-score < -entry_threshold (e.g., -2.0 means 2 std devs below mean)
        if self.pos[symbol] == 0 and z_score < -self.factor[0]:
            self.pos[symbol] = 1
            self.entry_price[symbol] = current_price
            self.entry_std[symbol] = std_dev  # Store std dev at entry for exit calculations
            return 1
        
        # Take Profit: Exit if price rises exit_threshold std devs above entry
        if self.pos[symbol] == 1:
            price_change_std = (current_price - self.entry_price[symbol]) / self.entry_std[symbol]
            
            if price_change_std > self.factor[1]:  # Recovered enough (take profit)
                self.pos[symbol] = 0
                return -1

        return 0
