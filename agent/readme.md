## MICRO CAP
Small cap - 300 million to 2 billion, micro cap - 50 million towh 300 million
consider russell 2000 (small cap ETF). 
Small cap still has a lot of institutional investors, no edge
*buy high value, industry trending, low risk firms*

1) Get all available tickers from NASDAQ (listed and other listed)
2) Use Alpaca to loosely filter by price and daily volume (USD1-20, $300k to $20M)
3) Use yfinance to retrieve market cap. per definition, it should be under $300M market cap

look at P/E, EBITDA, financial statements, debt
look at twitter, reddit etc.
look at whether the company is startup or trending up/down

## TO DO
- compute metrics (P/E, EBITDA). use AI agent to scrape, then retrieve market cap (or price) to actually compute the metrics. 
- ensure correctness by getting FORM TYPE IE QUARTERLY OR YEARLY

#### Agents List
- Footnotes extraction agent
- Insider trading (form4) labelling
- News classification (by industry)
- News Summary Agent
- Social Media Agent
- Risk management agent

### STAGE 0 - Initial Filter
- Filter by Alpaca Volume and price
- Filter by Market cap
- Get fundamentals & **report Footnotes** from SEC. calculate extra metrics (P/E, EBITDA, Burn Rate) - focus on cash burn rate. <- *footnotes parsing agent*

### STAGE 1 - prep stage (any time)
- SQLITE table: for FORM4 SEC filings of insider trading **table transactions** <- *insider trading labeling agent* to identify valid buys, who is the purchaser. 1. classifies as informed or routine 2. cross reference with 13D (recent) and 13F (historical) filings 
- SQLITE TAble: Industry classification get past news for each industry, and then map tickers to it based on correlation (price and volume) with industry news (reuters, finnhub), with scoring function. **table tickers** <- *LLM News classification agent*
- SQLITE table: industry cross correlations (ticker level and industry level, ie average amongs micro cap stocks) **table correlations** x2
- SQLITE table: Get more information on the tickers (short description, past important news) **table tickers** <- *LLM news summarizer agent*
- relative volume tool - compares the industry trading volume with the ticker trading volume **table tickers**

Outputs:
- 5 SQLITE tables
- filtered tickers based on terrible financials and clear signs of bankruptcy

### STAGE 2: Market analysis (live)
- market analysis tool, including bid-ask spread skew, stationarity, volume, trend, anomaly detection. create agent that compares market vs financials
- valuation framing tool (mapping type of business - cash burning/asset heavy/ profitable/ growing but unprofitable)
- social media activity per ticker, bot activity vs real activity <- *LLM social media agent*
- latest news activity (incl S-3 or 424B filings) for total industry <- *LLM News classification agent*
- get an update for all values in **STAGE 1**

Outputs:
- Social media & news activity per ticker
- updated 5 DBs
- Company financial status, with labels

### STAGE 3: Final Decider
- Risk management agent - 1. based on all TEXTUAL information, determine which stocks are flagged as risky, comparing with industry 2. tool for assessing high correlation stocks. 3. map risks to stocks
- Entry price, Position sizing and stop loss setting for portfolio construction. 

#### note: **table industry** should only focus on large industry moves. small specific news will be retrieved elsewehre.



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