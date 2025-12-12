from datetime import datetime, timedelta, timezone
import threading
import json
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, OptionBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed, OptionsFeed
from alpaca.data.live import StockDataStream
from config import Config

from abc import ABC, abstractmethod


class DataClient(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_history(self, symbols, n_days, interval):
        pass

    
class StockClient:

    def __init__(self, params = None):
        self.client = StockHistoricalDataClient(Config.ALPACA_KEY, Config.ALPACA_SECRET)

        
    def get_history(self,symbols, n_days, interval):
        """minute level day history for today"""

        day  = datetime.today()  - timedelta(days=n_days)
        start, end  = self.US_trading_hours(day)
        interval = interval.lower()
        if interval == 'minute':
            timeframe = TimeFrame.Minute
        elif interval == 'hour':
            timeframe = TimeFrame.Hour
        else: # default day
            timeframe = TimeFrame.Day

        req = StockBarsRequest(symbol_or_symbols=symbols,
                            timeframe=timeframe,
                              feed=DataFeed.IEX, start = start, end = datetime.now()) 
        
        return self.client.get_stock_bars(req).df

        

    def US_trading_hours(self, day = datetime.now(timezone.utc)):
        # Ensure day is timezone aware
        if day.tzinfo is None:
            day = day.replace(tzinfo=timezone.utc)
            
        start = datetime(day.year, day.month, day.day, 13, 30, tzinfo=timezone.utc)  # 9:30 AM ET
        end   = datetime(day.year, day.month, day.day, 20, 0, tzinfo=timezone.utc)
        return start, end

class OptionsClient():
    def __init__(self):
        self.client = OptionHistoricalDataClient(Config.ALPACA_KEY, Config.ALPACA_SECRET)
    def get_history(self,symbols, n_days, interval):
        """minute level day history for today"""

        day  = datetime.today()  - timedelta(days=n_days)
        start, end  = self.US_trading_hours(day)
        interval = interval.lower()
        if interval == 'minute':
            timeframe = TimeFrame.Minute
        elif interval == 'hour':
            timeframe = TimeFrame.Hour
        else: # default day
            timeframe = TimeFrame.Day

        req = OptionBarsRequest(symbol_or_symbols=symbols,
                            timeframe=timeframe,
                              feed=OptionsFeed.INDICATIVE, start = start, end = datetime.now(timezone.utc)- timedelta(minutes=16)) 
        
        return self.client.get_option_bars(req).df


class LiveDataClient:
    def __init__(self):
        self.client = StockDataStream(Config.ALPACA_KEY, Config.ALPACA_SECRET, url_override="wss://stream.data.alpaca.markets/v2/test")
        self.latest = None
        self._thread = None

    async def _quote_handler(self, quote):
        self.latest = quote.to_dict() if hasattr(quote, "to_dict") else str(quote)

    def get_quote(self, symbols):
        for s in symbols:
            self.client.subscribe_quotes(self._quote_handler, s)
        self._thread = threading.Thread(target=self.client.run, daemon=True)
        self._thread.start()

    def latest_json(self):
        return json.dumps(self.latest, default=str)

    def stop(self):
        try:
            self.client.stop()
        except Exception:
            pass

