import requests
import pandas as pd
import numpy as np

class Fundamentals:
    def __init__(self, tickers: list[str]):
        self.df = self.get_fundamentals(tickers)



    def _get_json(self, url: str, headers : dict):
        r = requests.get(url, headers=headers, timeout = 30)
        r.raise_for_status()
        return r.json()
    
    def extract_data(self, data: dict) -> dict:
        def safe_get(path: list, default=None):
            cur = data
            for p in path:
                if not isinstance(cur, dict) or p not in cur:
                    return default
                cur = cur[p]
            return cur

        assets = []
        for item in safe_get(['facts','us-gaap','Assets','units','USD'], []):
            assets.append((item.get('end'), item.get('val')))

        liabilities = []
        for item in safe_get(['facts','us-gaap','Liabilities','units','USD'], []):
            liabilities.append((item.get('end'), item.get('val')))

        cash = []
        for item in safe_get(['facts','us-gaap','CashAndCashEquivalentsAtCarryingValue','units','USD'], []):
            cash.append((item.get('end'), item.get('val')))

        shares = []
        for item in safe_get(['facts','dei','EntityCommonStockSharesOutstanding','units','shares'], []):
            shares.append((item.get('end'), item.get('val')))

        net_income = []
        for item in safe_get(
            ['facts','us-gaap','NetIncomeLossAvailableToCommonStockholdersBasic','units','USD'],
            []
        ):
            net_income.append((item.get('end'), item.get('val')))

        revenue = []
        for item in safe_get(['facts','us-gaap','Revenues','units','USD'], []):
            revenue.append((item.get('end'), item.get('val')))

        ebit = []
        for item in safe_get(['facts','us-gaap','OperatingIncomeLoss','units','USD'], []):
            ebit.append((item.get('end'), item.get('val')))

        operatingcashflow = []
        for item in safe_get(
            ['facts','us-gaap','NetCashProvidedByUsedInOperatingActivities','units','USD'],
            []
        ):
            operatingcashflow.append((item.get('end'), item.get('val')))

        debt = []
        for item in safe_get(['facts','us-gaap','LongTermDebt','units','USD'], []):
            debt.append((item.get('end'), item.get('val')))

        return {
            "assets": assets,
            "liabilities": liabilities,
            "cash": cash,
            "shares": shares,
            "net_income": net_income,
            "revenue": revenue,
            "ebit": ebit,
            "operating_cash_flow": operatingcashflow,
            "long_term_debt": debt,
        }

    def get_edgar(self, cik):
        """Fetches the EDGAR company facts JSON for a given CIK. Data time period varies among companies"""
        COMPANYFACTS_URL_TMPL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        headers = {"User-Agent": "leo@gmail.com", "Accept-Encoding": "gzip, deflate"}
        url = COMPANYFACTS_URL_TMPL.format(cik=cik)
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def json_to_df(self, edgar_json: dict) -> pd.DataFrame:
    
        rows = []

        for ticker, metrics in edgar_json.items():
            row = {"ticker": ticker}
            row["CIK"] =metrics.get("CIK", "")

            # helper: parse list of (end, val) safely
            def _sorted_vals(key):
                vals = metrics.get(key, [])
                # keep only pairs with end and val
                vals = [(d, v) for d, v in vals if d is not None and v is not None]
                return sorted(vals, key=lambda x: x[0])

            # helper: record_date = latest end date across selected keys
            record_dates = []
            for key in ["assets", "liabilities", "cash", "shares", "long_term_debt",
                        "revenue", "net_income", "ebit", "operating_cash_flow"]:
                vals = _sorted_vals(key)
                if vals:
                    record_dates.append(vals[-1][0])
            row["record_date"] = max(record_dates) if record_dates else np.nan

            # ---- STOCK METRICS: take latest ----
            for key in ["assets", "liabilities", "cash", "shares", "long_term_debt"]:
                vals = _sorted_vals(key)
                row[key] = vals[-1][1] if vals else np.nan

            # ---- FLOW METRICS: TTM if possible else latest ----
            for key in ["revenue", "net_income", "ebit", "operating_cash_flow"]:
                vals = _sorted_vals(key)
                if len(vals) >= 4:
                    row[key] = sum(v for _, v in vals[-4:])
                elif vals:
                    row[key] = vals[-1][1]
                else:
                    row[key] = np.nan

            # ---- YoY comparisons for 3 important flow metrics ----
            # Simple: compare latest value vs a value ~1 year earlier (within a tolerance window)
            def _yoy(key):
                vals = _sorted_vals(key)
                if len(vals) < 2:
                    return np.nan

                # convert date strings to pandas datetime for comparisons
                dfv = pd.DataFrame(vals, columns=["end", "val"])
                dfv["end"] = pd.to_datetime(dfv["end"], errors="coerce")
                dfv["val"] = pd.to_numeric(dfv["val"], errors="coerce")
                dfv = dfv.dropna(subset=["end", "val"]).sort_values("end")
                if len(dfv) < 2:
                    return np.nan

                latest_end = dfv["end"].iloc[-1]
                latest_val = dfv["val"].iloc[-1]

                # target ~1 year before
                target = latest_end - pd.Timedelta(days=365)
                dfv["diff_days"] = (dfv["end"] - target).abs().dt.days

                # pick closest within a loose window (handles annual-only or irregular reporting)
                candidate = dfv.iloc[:-1].sort_values("diff_days").head(1)
                if candidate.empty:
                    return np.nan
                if candidate["diff_days"].iloc[0] > 430:  # too far away
                    return np.nan

                prev_val = candidate["val"].iloc[0]
                if prev_val == 0 or not np.isfinite(prev_val) or not np.isfinite(latest_val):
                    return np.nan

                return (latest_val - prev_val) / abs(prev_val)

            row["assets_yoy"] = _yoy("assets")
            row["net_income_yoy"] = _yoy("net_income")
            row["operating_cash_flow_yoy"] = _yoy("operating_cash_flow")

            rows.append(row)

        return pd.DataFrame(rows)

    def get_fundamentals(self, tickers):
        SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
        headers = {"User-Agent": "leo@gmail.com", "Accept-Encoding": "gzip, deflate"}    
        CIK= self._get_json(SEC_TICKER_MAP_URL, headers)
        out = {}
        print(f"Processing {len(tickers)} CIK data...")
        CIK_data = CIK['data']
        counter = 1
        for item in CIK_data:
            
            if item[2].upper() in tickers:
                CIK_code = str(item[0]).zfill(10) 
                try:
                    data = self.get_edgar(CIK_code)
                except (requests.RequestException) as e:
                    print(f"Error fetching data for CIK {CIK_code} ({item[2].upper()}): {e}")
                    counter+=1
                    continue
                extracted = self.extract_data(data)
                extracted["CIK"] = CIK_code
                out[item[2].upper()] = extracted

                
                print(f"Processed {len(out)+counter} / {len(tickers)}")
        

        return self.json_to_df(out)
