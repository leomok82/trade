import pandas as pd

class Cache:
    def __init__(self, path):
        self.path = path

    def check(self, symbol, begin, end):
        try:
            df.read_parquet(self.path.format(symbol)).query("timestamp >= @begin and timestamp <= @end")