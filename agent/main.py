
from preprocess import *


if __name__ == "__main__":
    load_environment()

    try:
         df = pd.read_csv("data/fundamentals.csv")

    except FileNotFoundError:
        try:
            with open("data/filtered_tickers.txt", "r") as f:
                tickers = [line.strip() for line in f.readlines()]
            print(f"Loaded {len(tickers)} tickers from file.")

        except FileNotFoundError:
            tickers = TickerInfo()
            tickers.alpaca_filter()
            tickers.market_cap_filter(min_market_cap = 50_000_000, max_market_cap = 400_000_000)
            tickers.save_symbols(filepath="data/filtered_tickers.txt")
        fundamentals = Fundamentals(tickers)
        fundamentals.df.to_csv("data/fundamentals.csv", index=False)
        df = fundamentals.df
    
    update_form4_db(30, df['CIK'].tolist())
    