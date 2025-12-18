# Strategy Visualization Guide

This guide explains how to use the `StrategyVisualizer` class to visualize trading strategy performance.

## Overview

The `StrategyVisualizer` class provides comprehensive visualization capabilities for backtesting results, including:

- **Equity Curve**: Track total equity, cash, and position values over time
- **Cumulative P&L**: Visualize profit and loss accumulation
- **Drawdown Analysis**: Monitor portfolio drawdowns
- **Trade Signals**: Plot buy/sell signals on price charts
- **Position Tracking**: Monitor position sizes over time
- **Performance Dashboard**: Comprehensive multi-panel visualization

## Quick Start

### 1. Basic Usage with BacktestEngine

The visualizer is automatically integrated with the `BacktestEngine`:

```python
from src.engine import BacktestEngine
from src.strategy import BuyLow

# Initialize strategy
strategy = BuyLow(factor=(3, 2), stop_loss=3)

# Initialize engine with visualizer enabled
engine = BacktestEngine(
    strategy=strategy,
    data=data,
    symbols=['AAPL', 'MSFT'],
    initial_capital=10000,
    enable_visualizer=True  # Enable visualization
)

# Run backtest
equity_curve = engine.run()

# Access visualizer
visualizer = engine.visualizer
```

### 2. Generate Visualizations

```python
# Print summary statistics
visualizer.print_summary()

# Create comprehensive dashboard
visualizer.plot_all(figsize=(16, 12), save_path='results/dashboard.png')

# Individual plots
visualizer.plot_equity_curve(save_path='results/equity.png')
visualizer.plot_cumulative_profit(save_path='results/profit.png')
visualizer.plot_trades(save_path='results/trades.png')
visualizer.plot_positions(save_path='results/positions.png')
```

## Visualization Methods

### `plot_all(figsize, save_path)`

Creates a comprehensive dashboard with multiple panels:
- Equity curve
- Cumulative P&L
- Drawdown
- Trade distribution by symbol
- Returns distribution

**Parameters:**
- `figsize`: Tuple (width, height) in inches, default (16, 12)
- `save_path`: Optional path to save the figure

**Example:**
```python
visualizer.plot_all(figsize=(16, 12), save_path='dashboard.png')
```

### `plot_equity_curve(figsize, save_path)`

Plots the equity curve showing:
- Total equity over time
- Cash balance
- Position value
- Initial capital reference line
- Drawdown subplot

**Example:**
```python
visualizer.plot_equity_curve(figsize=(14, 8), save_path='equity.png')
```

### `plot_cumulative_profit(figsize, save_path)`

Visualizes cumulative profit/loss with:
- P&L line chart
- Green fill for profits
- Red fill for losses
- Zero reference line

**Example:**
```python
visualizer.plot_cumulative_profit(figsize=(14, 8), save_path='profit.png')
```

### `plot_trades(symbol, figsize, save_path)`

Plots price charts with buy/sell signals:
- Price line for each symbol
- Green triangles (^) for buy signals
- Red triangles (v) for sell signals

**Parameters:**
- `symbol`: Specific symbol to plot (None = all symbols)
- `figsize`: Figure size
- `save_path`: Optional save path

**Example:**
```python
# Plot all symbols
visualizer.plot_trades(figsize=(14, 10), save_path='trades.png')

# Plot specific symbol
visualizer.plot_trades(symbol='AAPL', figsize=(14, 6))
```

### `plot_positions(figsize, save_path)`

Shows position sizes over time for each symbol.

**Example:**
```python
visualizer.plot_positions(figsize=(14, 8), save_path='positions.png')
```

### `get_summary_stats()`

Returns a dictionary of performance metrics:
- Initial Capital
- Final Equity
- Total Return
- Total P&L
- Max Drawdown
- Sharpe Ratio
- Total Trades
- Average Return per Trade

**Example:**
```python
stats = visualizer.get_summary_stats()
for key, value in stats.items():
    print(f"{key}: {value}")
```

### `print_summary()`

Prints formatted summary statistics to console.

**Example:**
```python
visualizer.print_summary()
```

## Manual Usage (Without BacktestEngine)

You can also use the visualizer independently:

```python
from src.visualizer import StrategyVisualizer

# Initialize
visualizer = StrategyVisualizer(
    symbols=['AAPL', 'MSFT'],
    initial_capital=10000
)

# Update during your strategy loop
for timestamp, bar in data.iterrows():
    # ... your strategy logic ...
    
    visualizer.update(
        timestamp=timestamp,
        equity=current_equity,
        cash=available_cash,
        positions={'AAPL': 100, 'MSFT': 50},
        last_prices={'AAPL': 150.0, 'MSFT': 300.0},
        signal=1,  # 1=buy, -1=sell, 0=hold
        symbol='AAPL',
        price=150.0
    )

# Generate visualizations
visualizer.plot_all()
```

## Complete Example

See `example_visualization.py` for a complete working example:

```bash
python trade/example_visualization.py
```

This script:
1. Loads data from Alpaca
2. Runs a backtest with the BuyLow strategy
3. Generates all visualizations
4. Saves results to `trade/results/`

## Output Files

When using `save_path`, visualizations are saved as high-resolution PNG files (300 DPI):

```
trade/results/
├── dashboard.png          # Comprehensive dashboard
├── equity_curve.png       # Equity and drawdown
├── cumulative_profit.png  # P&L over time
├── trade_signals.png      # Price charts with signals
├── positions.png          # Position sizes
└── trades.csv            # Trade log
```

## Customization

### Figure Size

Adjust figure size for different displays:

```python
# Larger for presentations
visualizer.plot_all(figsize=(20, 15))

# Smaller for reports
visualizer.plot_all(figsize=(12, 9))
```

### Styling

The visualizer uses matplotlib and seaborn. You can customize the style:

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Set style before plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

visualizer.plot_all()
```

## Performance Metrics

The visualizer tracks and calculates:

- **Total Return**: (Final Equity - Initial Capital) / Initial Capital
- **Sharpe Ratio**: Risk-adjusted return (annualized)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Average Return**: Mean return per trade

## Tips

1. **Save Visualizations**: Always use `save_path` to preserve results
2. **Check Summary First**: Use `print_summary()` before generating plots
3. **Multiple Symbols**: The visualizer handles multi-symbol strategies automatically
4. **Memory**: For long backtests, consider plotting periodically or using subsets
5. **Comparison**: Run multiple backtests and compare saved visualizations

## Troubleshooting

### No Data to Plot

If you see "No data to plot", ensure:
- The backtest has run (`engine.run()`)
- The visualizer is enabled (`enable_visualizer=True`)
- Data was loaded successfully

### Import Errors

Ensure required packages are installed:

```bash
pip install matplotlib seaborn pandas numpy
```

### Memory Issues

For very large datasets:
- Reduce the date range
- Use higher timeframes (e.g., 5Min instead of 1Min)
- Plot specific symbols instead of all

## Integration with Strategy

The visualizer automatically tracks:
- Every bar processed
- All trade signals
- Position changes
- Equity updates

No manual tracking required when using `BacktestEngine`!

## Next Steps

- Explore `example_visualization.py` for a complete example
- Customize visualizations for your needs
- Integrate with your existing strategies
- Compare different strategy parameters visually

For more information, see the main README.md and strategy documentation.