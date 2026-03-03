# Enhanced Fundamentals Extraction with LLM

## Overview

The enhanced `fundamentals.py` module now includes:

1. **SEC Filing Caching**: Downloads and caches 10-K/10-Q filings for each company
2. **LLM-Based Field Extraction**: Uses Claude 3.5 Sonnet via OpenRouter to intelligently find missing fundamental fields
3. **Online Search Fallback**: Uses DuckDuckGo (free, no API key needed) to search for alternative data sources

## Installation

```bash
cd agent
pip install -r requirements.txt
```

## Required API Keys

### OpenRouter API Key (Required for LLM features)
Get a free API key at: https://openrouter.ai/
```bash
export API_KEY="your-openrouter-api-key"
```

**Note**: DuckDuckGo search is completely free and requires no API key!

## Usage

### Basic Usage (with LLM enabled)
```python
from preprocess.fundamentals import Fundamentals

tickers = ["AAPL", "MSFT", "GOOGL"]
fund = Fundamentals(tickers, use_llm=True)
df = fund.df
```

### Without LLM (original behavior)
```python
fund = Fundamentals(tickers, use_llm=False)
```

### With Custom API Key
```python
fund = Fundamentals(
    tickers,
    use_llm=True,
    api_key="your-openrouter-key"
)
```

## How It Works

### 1. Standard XBRL Extraction
First attempts to extract fundamentals using predefined XBRL tag mappings from SEC's Company Facts API.

### 2. SEC Filing Cache
If fields are missing, downloads and caches the latest 10-K or 10-Q filing metadata:
- Stored in `agent/data/sec_filings/`
- Cached to avoid repeated downloads
- Includes filing type, date, and accession number

### 3. LLM Analysis
When fields are missing, the LLM:
- Analyzes available XBRL tags in the filing
- Suggests alternative tag names that might contain the data
- Provides confidence levels for suggestions
- Recommends calculation methods if direct tags don't exist

### 4. DuckDuckGo Search Fallback
If LLM can't find the data in SEC filings:
- Uses DuckDuckGo (free) to search the web for the specific metric
- Uses LLM to extract numerical values from search results
- Handles common formats (B for billions, M for millions)
- Validates and formats the data

## Supported Metrics

- **revenue**: Total revenue/sales
- **net_income**: Net income available to common shareholders
- **ebit**: Operating income/EBIT
- **cash**: Cash and cash equivalents
- **assets**: Total assets
- **liabilities**: Total liabilities
- **long_term_debt**: Long-term debt
- **operating_cash_flow**: Cash from operations
- **shares**: Shares outstanding
- **da**: Depreciation and amortization

## Example Output

```python
print(fund.df.head())
```

Output includes:
- All standard fundamental metrics
- CIK numbers
- Dates for balance sheet items
- Missing fields filled by LLM/search when possible

## Performance Considerations

- **Caching**: SEC filings are cached locally to reduce API calls
- **Rate Limiting**: Respects SEC API rate limits (10 requests/second)
- **LLM Costs**: Claude 3.5 Sonnet via OpenRouter (~$3 per 1M input tokens, $15 per 1M output tokens)
- **Free Search**: DuckDuckGo search is completely free with no rate limits
- **Batch Processing**: Progress updates every 20 tickers

## Troubleshooting

### Missing Dependencies
```bash
pip install langchain langchain-openai langchain-community duckduckgo-search
```

### API Key Errors
Ensure environment variable is set:
```bash
echo $API_KEY
```

### Rate Limiting
If you hit SEC rate limits, add delays:
```python
import time
time.sleep(0.1)  # 100ms delay between requests
```

## Future Enhancements

- [ ] Parse actual 10-K/10-Q HTML/XML content (not just metadata)
- [ ] Support for international companies (non-US GAAP)
- [ ] Custom metric definitions
- [ ] Historical data extraction (multiple years)
- [ ] Automated tag learning from successful extractions