"""
Example script demonstrating how to use the StrategyVisualizer with the BacktestEngine.
"""

import pandas as pd
from src.engine import BacktestEngine
from src.strategy import BuyLow
from src.alpaca_loader import AlpacaDataLoader
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """
    Run a backtest with visualization enabled.
    """
    
    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL']  # Example symbols
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    initial_capital = 10000
    
    print("="*60)
    print("BACKTESTING WITH VISUALIZATION")
    print("="*60)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print("="*60 + "\n")
    
    # Load data
    print("Loading data from Alpaca...")
    loader = AlpacaDataLoader(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY'),
        base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    )
    
    data = loader.load_bars(
        symbols=symbols,
        start=start_date,
        end=end_date,
        timeframe='1Min'
    )
    
    if data.empty:
        print("No data loaded. Please check your API credentials and date range.")
        return
    
    print(f"Loaded {len(data)} bars\n")
    
    # Initialize strategy
    print("Initializing BuyLow strategy...")
    strategy = BuyLow(
        factor=(3, 2),
        stop_loss=3,
        timeframe_minutes=390,
        use_regime=True,
        regime_adjust=True,
        use_trend=True
    )
    
    # Initialize engine with visualizer enabled
    print("Initializing backtest engine with visualizer...\n")
    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        symbols=symbols,
        initial_capital=initial_capital,
        enable_visualizer=True  # Enable visualization
    )
    
    # Run backtest
    print("Running backtest...")
    equity_curve = engine.run()
    print("Backtest complete!\n")
    
    # Get statistics
    stats = engine.get_stats()
    print("="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    for key, value in stats.items():
        print(f"{key:.<40} {value}")
    print("="*60 + "\n")
    
    # Access the visualizer
    visualizer = engine.visualizer
    
    if visualizer:
        # Print summary statistics
        visualizer.print_summary()
        
        # Generate visualizations
        print("Generating visualizations...\n")
        
        # 1. Comprehensive dashboard
        print("1. Creating comprehensive dashboard...")
        visualizer.plot_all(figsize=(16, 12), save_path='trade/results/dashboard.png')
        
        # 2. Equity curve with drawdown
        print("2. Creating equity curve...")
        visualizer.plot_equity_curve(figsize=(14, 8), save_path='trade/results/equity_curve.png')
        
        # 3. Cumulative profit
        print("3. Creating cumulative profit chart...")
        visualizer.plot_cumulative_profit(figsize=(14, 8), save_path='trade/results/cumulative_profit.png')
        
        # 4. Trade signals for each symbol
        print("4. Creating trade signal charts...")
        visualizer.plot_trades(figsize=(14, 10), save_path='trade/results/trade_signals.png')
        
        # 5. Position sizes over time
        print("5. Creating position size chart...")
        visualizer.plot_positions(figsize=(14, 8), save_path='trade/results/positions.png')
        
        print("\nAll visualizations saved to trade/results/")
        print("="*60)
    else:
        print("Visualizer not enabled.")
    
    # Get trades DataFrame
    trades_df = engine.get_trades()
    if not trades_df.empty:
        print(f"\nTotal trades executed: {len(trades_df)}")
        print("\nFirst 10 trades:")
        print(trades_df.head(10))
        
        # Save trades to CSV
        trades_df.to_csv('trade/results/trades.csv', index=False)
        print("\nTrades saved to trade/results/trades.csv")
    
    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Create results directory if it doesn't exist
    os.makedirs('trade/results', exist_ok=True)
    
    main()

# Made with Bob
