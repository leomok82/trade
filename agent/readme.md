## MICRO CAP
Small cap - 300 million to 2 billion, micro cap - 50 million towh 300 million
consider russell 2000 (small cap ETF). 
Small cap still has a lot of institutional investors, no edge

1) Get all available tickers from NASDAQ (listed and other listed)
2) Use Alpaca to loosely filter by price and daily volume (USD1-20, $300k to $20M)
3) Use yfinance to retrieve market cap. per definition, it should be under $300M market cap

look at P/E, EBITDA, financial statements, debt
look at twitter, reddit etc.
look at whether the company is startup or trending up/down

## TO DO
- compute metrics (P/E, EBITDA)

STAGE 1:
- create market analysis tool, including stationarity, volume, trend, anomaly detection. create agent that compares market vs financials
- create financial report getter
- valuation framing (mapping type of business - cash burning/asset heavy/ profitable/ growing but unprofitable)
- create search for insider trades

STAGE 2:
- event mapper - map whether past events affected this stock
- create social media getter (reddit, X)
- create news getter (including reuters, fninhub)
- industry news getter -> RAG? 

also try factor tilt and quant screen.

### IBANK FLOW (FROMT OPENAI)
→ Investability screening
→ Economic relevance screening
→ Valuation framing
→ Risk & scenario analysis
→ Portfolio construction
→ Ongoing monitoring

#### Backtesting
not really possible to backtest, but we can get historical market cap data, historical news and check