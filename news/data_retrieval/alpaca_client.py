from abc import ABC, abstractmethod
from typing import Any, Dict, List
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

class DataProvider(ABC):
    @abstractmethod
    def get_historical_data(self, symbol: str, limit: int) -> List[Dict]:
        pass

class AlpacaDataProvider(DataProvider):
    def __init__(self, api_key: str, api_secret: str, base_url: str = None):
        # StockHistoricalDataClient uses separate URLs for data, so base_url (trading api) 
        # is largely irrelevant here unless used for url_override, but we'll accept it
        # to match the interface.
        self.client = StockHistoricalDataClient(api_key, api_secret)

    def get_historical_data(self, symbols: list, limit: int = 100, interval: str = 'minute') -> List[Dict]:
        """
        Fetches historical bars for a symbol.
        Returns a list of dictionaries (normalized data).
        """
        request_params = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            limit=limit
        )
        if interval == 'minute':
            timeframe = TimeFrame.Minute
        elif interval == 'hour':
            timeframe = TimeFrame.Hour
        else: # default day
            timeframe = TimeFrame.Day
        try:
            bars = self.client.get_stock_bars(request_params)
            
            # bars.data is a dict where key is symbol and value is list of bars
            if symbol in bars.data:
                # Convert Bar objects to dictionaries
                data_list = [
                    {
                        "timestamp": bar.timestamp,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "trade_count": bar.trade_count,
                        "vwap": bar.vwap
                    }
                    for bar in bars.data[symbol]
                ]
                return data_list
            return []
            
        except Exception as e:
            print(f"Error fetching data from Alpaca: {e}")
            return []
