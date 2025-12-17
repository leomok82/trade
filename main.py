import argparse
import pandas as pd
from src.alpaca_loader import StockClient
from src.strategy import *
from src.engine import BacktestEngine
from src.monte_carlo import MonteCarloSimulator
from src.webull_executor import WebullExecutor
from datetime import datetime, timedelta

def run_backtest(symbols, days = 365, use_regime=True):
    print(f"Running backtest for {symbols}...")
    loader = StockClient()
    # view 2024 data for backtest
    end_date = datetime.now() #- timedelta(days=365)
    print(f"Loading data from {end_date.date()} for {days} days...")
    data = loader.get_history(symbols, lookback = days, end = end_date, interval= 'minute')
    print(f"Data Retrieved: {data.shape[0]} bars")

    print("Initializing strategy...")
    strategy = BuyLow(factor=(0.6,0.6), stop_loss = 0.6, timeframe_minutes = 390*5, use_regime=use_regime, regime_adjust=use_regime) #0.2,0.4,1
    print(f"Strategy Implemented (Regime: {use_regime})")
    
    print("Running backtest engine...")
    engine = BacktestEngine(strategy, data, symbols)
    results = engine.run()
    print(f"Backtest complete: {results.shape[0]} equity points")

    
    print("\nPerformance Statistics:")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")
        
    print("\nRecent Trades:")
    print(engine.get_trades().tail())

    # Monte Carlo Simulation``
    print("\n" + "="*60)
    print("Monte Carlo Risk Analysis")
    print("="*60)
    returns = results['equity'].pct_change().dropna()
    initial_value = results['equity'].iloc[-1]
    
    mc = MonteCarloSimulator(returns, num_simulations=1000, num_days=252, initial_value=initial_value)
    mc_results = mc.run()
    
    print(f"\nCurrent Portfolio Value: ${initial_value:.2f}")
    print(f"Simulated {mc_results.shape[1]} paths over {mc_results.shape[0]} days\n")
    
    # Summary Statistics
    print("Summary Statistics:")
    mc_stats = mc.get_summary_stats()
    for k, v in mc_stats.items():
        print(f"  {k}: {v}")
    
    # Risk Metrics
    print("\nRisk Metrics:")
    var_95 = mc.calculate_var(0.95)
    var_99 = mc.calculate_var(0.99)
    cvar_95 = mc.calculate_cvar(0.95)
    cvar_99 = mc.calculate_cvar(0.99)
    
    print(f"  95% VaR: ${var_95:.2f} (5% chance of losing more)")
    print(f"  99% VaR: ${var_99:.2f} (1% chance of losing more)")
    print(f"  95% CVaR: ${cvar_95:.2f} (expected loss in worst 5%)")
    print(f"  99% CVaR: ${cvar_99:.2f} (expected loss in worst 1%)")
    
    # Percentile Analysis
    print("\nProjected Outcomes (1 Year):")
    percentiles = mc.get_percentiles([5, 25, 50, 75, 95])
    for p, value in percentiles.items():
        print(f"  {p} percentile: ${value:.2f}")
    
    # Confidence Interval
    lower, upper = mc.get_confidence_interval(0.95)
    print(f"\n95% Confidence Interval: ${lower:.2f} - ${upper:.2f}")

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
    parser.add_argument('--symbols', type=str, default=None, help='Symbols to trade')
    parser.add_argument('--days', type=int, default=30, help='Number of days for backtest (default: 30)')
    parser.add_argument('--regime', action='store_true', help='Enable regime detection (slower but more adaptive)')
    

    args = parser.parse_args()
    if args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = parse_symbols(args.symbols_path)
    
    if args.mode == 'backtest':
        run_backtest(symbols, days=args.days, use_regime=args.regime)
    # elif args.mode == 'live':
    #     run_live(args.symbol)

if __name__ == "__main__":
    main()

#['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN'], 365, 'minute'
