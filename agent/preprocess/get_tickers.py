import yfinance as yf
import requests
import io
import pandas as pd
import time

NASDAQLISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHERLISTED_URL  = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"


class TickerInfo:
    def __init__(self, urls: list[str], params=None):
        self.urls = urls
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
        self.symbols = self.get_symbols()
        
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
        return out
    
    def _download_ticker_list(self, url: str) -> pd.DataFrame:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        lines = [ln for ln in r.text.splitlines() if ln.strip() and not ln.startswith("File Creation Time")]
        data = io.StringIO("\n".join(lines))
        df = pd.read_csv(data, sep="|")
        return df

    def _tradable_symbols_alpaca(self, auth: dict) -> set[str]:
        trading_base = auth.get("ALPACA_TRADING_BASE_URL", self.params["ALPACA_TRADING_BASE_URL"]).rstrip("/")
        key_id = (auth.get("ALPACA_KEY") or "").strip()
        secret = (auth.get("ALPACA_SECRET") or "").strip()
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

    def alpaca_filter(self, auth: dict) -> list[str]:
        alpaca_base = auth.get("ALPACA_DATA_BASE_URL", self.params["ALPACA_DATA_BASE_URL"]).rstrip("/")
        key_id = (auth.get("ALPACA_KEY") or "").strip()
        secret = (auth.get("ALPACA_SECRET") or "").strip()
        headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret,
        }

        try:
            tradable = self._tradable_symbols_alpaca(auth)
            symbols = [s for s in self.symbols if s in tradable]
        except Exception as e:
            print(f"Alpaca tradable filter error: {e}")
            symbols = self.symbols

        price_min = float(self.params["PRICE_MIN"])
        price_max = float(self.params["PRICE_MAX"])
        dvol_min = float(self.params["DVOL_MIN"])
        dvol_max = float(self.params["DVOL_MAX"])
        snap_batch = int(self.params.get("ALPACA_SNAPSHOT_BATCH", 100))
        sleep_s = float(self.params.get("SLEEP_S", 1))

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
    
    def market_cap_filter(self, auth: dict = None) -> dict[str, int]:
        market_caps = {}
        symbols = self.symbols

        for idx, sym in enumerate(symbols):
            try:
                info = yf.Ticker(sym.replace(".", "-")).get_info()
                mc = info.get("marketCap")
                if mc is not None:
                    market_caps[sym] = mc
            except Exception as e:
                print(f"yfinance error {sym}: {e}")
            time.sleep(0.1)
        print(f"yfinance returned market cap for {len(market_caps)} tickers")
        self.symbols = list(market_caps.keys())
        return market_caps
    


