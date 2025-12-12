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
    def __init__(self, factor: tuple = (0.05, 0.03)):
        super().__init__()
        self.history = defaultdict(list)
        self.factor = factor
        self.entry_price = defaultdict(lambda: 1e8)
        self.pos = defaultdict(int)
        self.day_high = defaultdict(float)
       

    def on_bar(self, symbol, bar):
        self.history[symbol].append(bar['close'])
        if len(self.history[symbol]) <= 390:
            return 0
        self.day_high[symbol] = max(self.history[symbol][-int(60*6.5):])

        # Stop Loss
        if self.pos[symbol] == 1 and self.history[symbol][-1] < self.entry_price[symbol] * (1 - self.factor[1]):
            return -1

        # Buy
        if self.pos[symbol] == 0 and self.history[symbol][-1] < self.day_high[symbol] * (1 - self.factor[0]):
            self.pos[symbol] = 1
            self.entry_price[symbol] = self.history[symbol][-1]
            return 1
        
        if self.pos[symbol] == 1 and self.history[symbol][-1] > self.entry_price[symbol] * (1 + self.factor[1]):
            self.pos[symbol] = 0
            return -1

        return 0
