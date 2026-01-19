import yfinance as yf
import requests
import io
import pandas as pd
import time
import os

NASDAQLISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHERLISTED_URL  = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"


class TickerInfo:
    def __init__(self, urls: list[str] = None, params=None, tickers : list = None):
        self.urls = urls or [NASDAQLISTED_URL, OTHERLISTED_URL]
        self.params = params or {
            "BATCH_SIZE": 200,
            "ALPACA_SNAPSHOT_BATCH": 200,
            "PRICE_MIN": 0,
            "PRICE_MAX": 20.0,
            "DVOL_MIN": 100_000.0,
            "DVOL_MAX": 50_000_000.0,
            "SLEEP_S": 1,
            "ALPACA_DATA_BASE_URL": "https://data.alpaca.markets",
            "ALPACA_TRADING_BASE_URL": "https://paper-api.alpaca.markets",
        }
            
        self.symbols = tickers if tickers is not None else self.get_symbols()
    def get_symbols(self) -> list[str]:
        ls = []
        for url in self.urls:
            df = self._download_ticker_list(url)
            if 'ACT Symbol' in df.columns:
                ls.extend(df['ACT Symbol'].tolist())
            else:
                ls.extend(df['Symbol'].tolist())

        if len(ls) != len(set(ls)):
            print("Warning: Duplicate symbols found!")

        out = []
        for s in ls:
            sym = str(s).strip().upper()
            if sym.lower() == "nan" or not sym:
                continue
            if "$" in sym:
                continue
            if sym.endswith("ZZT"):
                continue
            if sym.endswith("W") and len(sym) > 1:
                continue
            if sym.endswith("U") and len(sym) > 1:
                continue
            if sym.endswith("R") and len(sym) > 1:
                continue
            if sym.endswith("-W"):
                continue
            out.append(sym)
        print(f"Symbols downloaded after cleaning: {len(out)}")
        return out
    
    def _download_ticker_list(self, url: str) -> pd.DataFrame:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        lines = [ln for ln in r.text.splitlines() if ln.strip() and not ln.startswith("File Creation Time")]
        data = io.StringIO("\n".join(lines))
        df = pd.read_csv(data, sep="|")
        return df

    def _tradable_symbols_alpaca(self) -> set[str]:
        trading_base = self.params["ALPACA_TRADING_BASE_URL"].rstrip("/")
        key_id = (os.getenv("ALPACA_KEY") or "").strip()
        secret = (os.getenv("ALPACA_SECRET") or "").strip()
        headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}

        res = requests.get(
            f"{trading_base}/v2/assets",
            params={"status": "active", "asset_class": "us_equity"},
            headers=headers,
            timeout=30,
        )
        res.raise_for_status()
        assets = res.json()
        return {a.get("symbol") for a in assets if a.get("tradable") is True and a.get("symbol")}

    def alpaca_filter(self) -> list[str]:
        print("Starting Alpaca filter...")

        alpaca_base = self.params.get("ALPACA_DATA_BASE_URL").rstrip("/")
        key_id = (os.getenv("ALPACA_KEY") or "").strip()
        secret = (os.getenv("ALPACA_SECRET") or "").strip()
        headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret,
        }

        try:
            tradable = self._tradable_symbols_alpaca()
            symbols = [s for s in self.symbols if s in tradable]
        except Exception as e:
            print(f"Alpaca tradable filter error: {e}")
            symbols = self.symbols
        print(f"Alpaca tradable symbols: {len(symbols)}")
        price_min = float(self.params["PRICE_MIN"])
        price_max = float(self.params["PRICE_MAX"])
        dvol_min = float(self.params["DVOL_MIN"])
        dvol_max = float(self.params["DVOL_MAX"])
        snap_batch = int(self.params.get("ALPACA_SNAPSHOT_BATCH", 100))
        sleep_s = float(self.params.get("SLEEP_S", 1))

        print("Proceeding to volatility and price filtering...")
        keep = []
        for i in range(0, len(symbols), snap_batch):
            batch = symbols[i:i + snap_batch]
            res = requests.get(
                f"{alpaca_base}/v2/stocks/snapshots",
                params={"symbols": ",".join(batch)},
                headers=headers,
                timeout=30,
            )
            res.raise_for_status()
            data = res.json()
            snaps = data.get("snapshots", data)

            for sym, snap in snaps.items():
                daily = (snap or {}).get("dailyBar") or {}
                px = daily.get("c")
                vol = daily.get("v")
                if px is None or vol is None:
                    continue
                dv = float(px) * float(vol)
                if price_min <= float(px) <= price_max and dvol_min <= dv <= dvol_max:
                    keep.append(sym)

            time.sleep(sleep_s)

        self.symbols = keep
        print(f"Alpaca filter kept {len(keep)} tickers")
        return keep
    
    def market_cap_filter(self, min_market_cap: int = 0, max_market_cap: int = 1e12) -> dict[str, int]:
        market_caps = {}
        symbols = self.symbols
        print("Starting market cap filter using yfinance...")
        print(f"Filtering {len(symbols)} symbols for market cap between {min_market_cap} and {max_market_cap}...")

        for idx, sym in enumerate(symbols):
            try:
                info = yf.Ticker(sym.replace(".", "-")).get_info()
                mc = info.get("marketCap")
                if mc is not None:
                    market_caps[sym] = int(mc)
            except Exception as e:
                print(f"yfinance error {sym}: {e}")
            time.sleep(0.1)

        filter_market_caps = {}
        for sym, market_cap in market_caps.items():
            if market_cap < max_market_cap and market_cap > min_market_cap:
                filter_market_caps[sym] = market_cap
        print(f"yfinance returned market cap for {len(filter_market_caps)} tickers after filtering ")

        if len(filter_market_caps) <= 0:
            print("Warning: No tickers passed market cap filter!")
        self.symbols = list(filter_market_caps.keys())
        
        return filter_market_caps
    
    def save_symbols(self, filepath: str):
        with open(filepath, "w") as f:
            for sym in self.symbols:
                f.write(f"{sym}\n")


if __name__ in "__main__":
    ti = TickerInfo(urls=[NASDAQLISTED_URL, OTHERLISTED_URL])
    print(f"Total tickers downloaded: {len(ti.symbols)}")
    # Example usage of filters
    # ti.alpaca_filter(auth={"ALPACA_KEY": "your_key", "ALPACA_SECRET": "your_secret"})
    # market_caps = ti.market_cap_filter()
