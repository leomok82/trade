import argparse
import pandas as pd
from src.alpaca_loader import StockClient
from src.strategy import *
from src.engine import BacktestEngine
from src.monte_carlo import MonteCarloSimulator
from src.webull_executor import WebullExecutor

def run_backtest(symbols, days = 365):
    print(f"Running backtest for {symbols}...")
    loader = StockClient()
    data = loader.get_history(symbols, days, 'minute')
    
    strategy = BuyLow(factor=(0.03, 0.03))
    engine = BacktestEngine(strategy, data, symbols)
    results = engine.run()

    
    print("\nPerformance Statistics:")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")
        
    print("\nRecent Trades:")
    print(engine.get_trades().tail())

    # # Monte Carlo
    # returns = results['equity'].pct_change().dropna()
    # mc = MonteCarloSimulator(returns)
    # mc_results = mc.run()
    # print("\nMonte Carlo Simulation (Last 5 runs):")
    # print(mc_results.iloc[-1].head())

def run_live(symbol):
    print(f"Starting live trading for {symbol}...")
    executor = WebullExecutor()
    executor.get_positions()
    # Logic for live trading loop would go here

def parse_symbols(path):
    with open(path, 'r') as f:
        symbols = f.read().splitlines()
    return symbols
def main():
    parser = argparse.ArgumentParser(description='Trading System')
    parser.add_argument('--mode', choices=['backtest', 'live'], help='Mode to run')
    parser.add_argument('--symbols_path', type=str, default='symbols.txt', help='Symbols to trade')
    parser.add_argument('--symbols', type=str, default='AAPL', help='Symbols to trade')
    

    args = parser.parse_args()
    if args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = parse_symbols(args.symbols_path)
    
    if args.mode == 'backtest':
        run_backtest(symbols)
    # elif args.mode == 'live':
    #     run_live(args.symbol)

if __name__ == "__main__":
    main()

#['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN'], 365, 'minute'
