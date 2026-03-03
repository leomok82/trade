from math import floor
import requests
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun

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

    def __init__(self, tickers: list[str], use_llm: bool = True, api_key: Optional[str] = None):
        self.tickers = [t.upper() for t in tickers]
        self.use_llm = use_llm
        self.cache_dir = Path("agent/data/sec_filings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM if enabled (using OpenRouter)
        if self.use_llm:
            openrouter_key = api_key or os.getenv("API_KEY")
            self.llm = ChatOpenAI(
                model="anthropic/claude-3.5-sonnet",
                temperature=0,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            
            # Initialize DuckDuckGo search (free, no API key needed)
            self.search_tool = DuckDuckGoSearchRun()
        
        self.df = self.get_fundamentals()

    def _get_json(self, url: str):
        headers = {"User-Agent": "YourName (your@email.com)"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

    def _download_filing(self, ticker: str, cik: str) -> Optional[Dict]:
        """Download and cache the latest 10-K or 10-Q filing"""
        cache_file = self.cache_dir / f"{ticker}_{cik}_filing.json"
        
        # Check cache first
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            # Get filing metadata
            submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            submissions = self._get_json(submissions_url)
            
            # Find most recent 10-K or 10-Q
            recent_filings = submissions.get('filings', {}).get('recent', {})
            forms = recent_filings.get('form', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            filing_dates = recent_filings.get('filingDate', [])
            
            filing_info = None
            for i, form in enumerate(forms):
                if form in ['10-K', '10-Q']:
                    filing_info = {
                        'form': form,
                        'accessionNumber': accession_numbers[i].replace('-', ''),
                        'filingDate': filing_dates[i],
                        'cik': cik
                    }
                    break
            
            if filing_info:
                # Cache the filing info
                with open(cache_file, 'w') as f:
                    json.dump(filing_info, f)
                
                print(f"Cached {filing_info['form']} filing for {ticker}")
                return filing_info
            
        except Exception as e:
            print(f"Error downloading filing for {ticker}: {e}")
        
        return None

    def _extract_with_llm(self, ticker: str, cik: str, missing_fields: List[str], facts: Dict) -> Dict:
        """Use LLM to extract missing fundamental fields"""
        if not self.use_llm or not missing_fields:
            return {}
        
        filing_info = self._download_filing(ticker, cik)
        if not filing_info:
            return {}
        
        # Create prompt for LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a financial analyst expert at extracting fundamental data from SEC filings.
Given a company's SEC filing information and available XBRL facts, extract the missing financial metrics.

Available XBRL tags in the filing:
{available_tags}

Missing metrics we need:
{missing_fields}

For each missing metric, analyze the available tags and provide:
1. The most appropriate XBRL tag name that could contain this data
2. The taxonomy (us-gaap, dei, or other)
3. Your confidence level (high/medium/low)

If you cannot find a suitable tag, suggest alternative data sources or calculation methods."""),
            ("user", "Company: {ticker}\nCIK: {cik}\nFiling Type: {filing_type}\nFiling Date: {filing_date}")
        ])
        
        # Get available tags from facts
        available_tags = []
        for taxonomy in facts.get('facts', {}).keys():
            available_tags.extend(list(facts['facts'][taxonomy].keys()))
        
        try:
            response = self.llm.invoke(
                prompt.format_messages(
                    ticker=ticker,
                    cik=cik,
                    filing_type=filing_info.get('form', 'Unknown'),
                    filing_date=filing_info.get('filingDate', 'Unknown'),
                    available_tags=', '.join(available_tags[:100]),  # Limit to first 100 tags
                    missing_fields=', '.join(missing_fields)
                )
            )
            
            # Parse LLM response and attempt to extract data
            print(f"LLM suggestions for {ticker}: {response.content[:200]}...")
            
            # TODO: Parse LLM response and extract suggested tags
            # This is a placeholder - you'd need to parse the LLM's structured output
            
        except Exception as e:
            print(f"LLM extraction error for {ticker}: {e}")
        
        return {}

    def _search_alternative_sources(self, ticker: str, missing_fields: List[str]) -> Dict:
        """Use DuckDuckGo search to find alternative data sources for missing fields"""
        if not self.search_tool or not missing_fields:
            return {}
        
        results = {}
        for field in missing_fields:
            try:
                query = f"{ticker} stock {field} latest financial data"
                search_result = self.search_tool.run(query)
                print(f"Search result for {ticker} {field}: {search_result[:150]}...")
                
                # Use LLM to extract numerical data from search results
                if self.use_llm:
                    extract_prompt = f"""From this search result, extract the numerical value for {field}:
{search_result}

Return only the number, or 'NOT_FOUND' if no clear value exists."""
                    
                    response = self.llm.invoke(extract_prompt)
                    value_str = response.content.strip()
                    
                    if value_str != 'NOT_FOUND':
                        try:
                            results[field] = float(value_str.replace(',', '').replace('$', '').replace('B', 'e9').replace('M', 'e6'))
                        except ValueError:
                            pass
                            
            except Exception as e:
                print(f"Search error for {ticker} {field}: {e}")
        
        return results

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
        missing_fields = []
        
        for category in self.TAG_MAP.keys():
            data = self.get_best_metric(facts, category)
            if not data:
                out[category] = np.nan
                missing_fields.append(category)
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
        
        # Try LLM extraction for missing fields
        if missing_fields and self.use_llm:
            print(f"Missing fields for {ticker}: {missing_fields}")
            llm_results = self._extract_with_llm(ticker, facts.get("cik", ""), missing_fields, facts)
            out.update(llm_results)
            
            # Update missing fields list
            still_missing = [f for f in missing_fields if f not in llm_results or pd.isna(llm_results[f])]
            
            # Try online search for remaining missing fields
            if still_missing and self.search_tool:
                search_results = self._search_alternative_sources(ticker, still_missing)
                out.update(search_results)
        
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

# Made with Bob
