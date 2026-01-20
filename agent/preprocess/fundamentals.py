from math import floor
import requests
import pandas as pd
import numpy as np

class Fundamentals:
    # Define Tag Prioritization
    TAG_MAP = {
        "revenue": [
            "Revenues", 
            "SalesRevenueNet", 
            "SalesRevenueGoodsNet", 
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "TotalRevenuesAndOtherIncome",
            "OperatingRevenueRevenue",
            "HealthCareOrganizationRevenue",
            "InterestAndDividendIncomeOperating", # For Banks
            "RealEstateRevenueNet",                # For REITs
            "RevenueFromContractWithCustomerIncludingAssessedTax"
        ],
        "net_income": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic","ProfitLoss","NetIncomeLossAvailableToCommonStockholdersDiluted"],
        "ebit": ["OperatingIncomeLoss", "IncomeLossFromOperationsBeforeIncomeTaxExpenseBenefit","OperatingProfitLoss"],
        "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "assets": ["Assets"],
        "liabilities": ["Liabilities","LiabilitiesCurrent","LiabilitiesAndStockholdersEquity"],
        "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
        "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
        "shares": ["EntityCommonStockSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
        "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"]
    }

    def __init__(self, tickers: list[str]):
        self.tickers = [t.upper() for t in tickers]
        self.df = self.get_fundamentals()

    def _get_json(self, url: str):
        headers = {"User-Agent": "YourName (your@email.com)"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_best_metric(self, facts, category):
        """Tries multiple XBRL tags for a category and returns the best list of data."""
        for tag in self.TAG_MAP[category]:
            # Check us-gaap first, then dei
            for taxonomy in ['us-gaap', 'dei']:
                try:
                    data = facts['facts'][taxonomy][tag]['units']
                    unit = 'USD' if 'USD' in data else 'shares'
                    return data[unit]
                except KeyError:
                    continue
        return []

    def process_facts(self, ticker, facts):
        out = {"ticker": ticker, "CIK": facts.get("cik", "")}
        
        for category in self.TAG_MAP.keys():
            data = self.get_best_metric(facts, category)
            if not data:
                out[category] = np.nan
                continue

            # Convert to DataFrame to handle dates and periods
            df_m = pd.DataFrame(data)
            df_m['end'] = pd.to_datetime(df_m['end'])
            
            # For Balance Sheet items (Instant): Take the latest
            if category in ["assets", "liabilities", "cash", "long_term_debt", "shares"]:
                latest = df_m.sort_values('end').iloc[-1]
                out[category] = latest['val']
                out[f"{category}_date"] = latest['end']
            
            # For Income/Cash Flow (Duration): Find TTM
            else:
                # Filter for 12-month periods (approx 365 days)
                if 'start' in df_m.columns:
                    df_m['start'] = pd.to_datetime(df_m['start'])
                    df_m['duration'] = (df_m['end'] - df_m['start']).dt.days
                    
                    # Look for the most recent 12-month value
                    ttm_data = df_m[(df_m['duration'] > 330) & (df_m['duration'] < 370)]
                    if not ttm_data.empty:
                        latest_ttm = ttm_data.sort_values('end').iloc[-1]
                        out[category] = latest_ttm['val']
                    else:
                        # Fallback to latest available if no 12-month period found
                        out[category] = df_m.sort_values('end').iloc[-1]['val']
                else:
                    out[category] = df_m.sort_values('end').iloc[-1]['val']
        
        return out

    def get_fundamentals(self):
        # 1. Get Ticker -> CIK mapping
        mapping_url = "https://www.sec.gov/files/company_tickers_exchange.json"
        mapping_data = self._get_json(mapping_url)
        
        # Convert mapping to searchable dict
        ticker_to_cik = {}
        for item in mapping_data['data']:
            ticker_to_cik[item[2].upper()] = str(item[0]).zfill(10)

        results = []
        for i, ticker in enumerate(self.tickers):
            cik = ticker_to_cik.get(ticker)
            if not cik:
                print(f"CIK not found for {ticker}")
                continue
            
            try:
                if i % 20 == 0:
                    print(f"Fundamentals Retrieval {floor((i+1)/len(self.tickers)*100)}% complete")
                facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                facts = self._get_json(facts_url)
                processed = self.process_facts(ticker, facts)
                results.append(processed)
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
        print(f"Fundamentals retrieval complete. {len(results)} / {len(self.tickers)} tickers processed successfully.")
        return pd.DataFrame(results)