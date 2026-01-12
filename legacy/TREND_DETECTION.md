# Trend Detection Implementation

## Overview
Added trend detection to the trading strategy to filter trades based on market direction. The strategy now only enters positions when the market is trending upward or sideways (flat), avoiding downtrends.

## New Files

### `src/trends.py`
Contains two main classes:

#### `TrendDirection` (Enum)
- `UP`: Clear uptrend (price rising consistently)
- `FLAT`: Sideways/ranging market (no clear direction)
- `DOWN`: Clear downtrend (price falling consistently)

#### `TrendDetector`
Detects market trends using three methods:
1. **Moving Average Crossover & Slope**: Compares short-term (50-bar) and long-term (200-bar) moving averages
2. **Linear Regression Slope**: Calculates the slope of recent price action
3. **Higher Highs / Lower Lows**: Analyzes price patterns across quarters

**Key Features:**
- Multi-method consensus (majority vote with MA weighted 2x)
- Configurable windows and thresholds
- Trend strength measurement (0-1)
- Helper method `is_tradeable()` to check if trend allows trading

#### `AdaptiveTrendDetector`
Enhanced version that adjusts thresholds based on volatility:
- In high volatility: Requires stronger signals to confirm trends
- Prevents false trend signals during choppy markets

## Integration with Strategy

### Updated `BuyLow` Strategy
New parameters:
- `use_trend` (bool, default=True): Enable/disable trend detection
- `allow_flat_trend` (bool, default=True): Allow trading in sideways markets

**Trading Logic:**
1. Update trend detector on each bar
2. Before entering a position, check trend:
   - ✅ **UP trend**: Always allow entry
   - ✅ **FLAT trend**: Allow if `allow_flat_trend=True`
   - ❌ **DOWN trend**: Block entry (avoid catching falling knives)
3. Exit logic remains unchanged (stop loss and take profit still active)

### New Methods
- `get_trend_info(symbol)`: Returns trend statistics including:
  - Current trend direction
  - Trend strength (0-1)
  - Short and long moving averages

## Usage

### Command Line
```bash
# Enable trend detection (default)
python main.py --mode backtest --symbols AAPL,MSFT --trend

# Disable trend detection
python main.py --mode backtest --symbols AAPL,MSFT --no-trend

# Combine with regime detection
python main.py --mode backtest --symbols AAPL,MSFT --regime --trend
```

### Programmatic
```python
from src.strategy import BuyLow

# With trend detection (only trade UP/FLAT)
strategy = BuyLow(
    factor=(0.6, 0.6),
    stop_loss=0.6,
    use_trend=True,
    allow_flat_trend=True
)

# Only trade in uptrends
strategy = BuyLow(
    factor=(0.6, 0.6),
    stop_loss=0.6,
    use_trend=True,
    allow_flat_trend=False  # Strict uptrend only
)

# Get trend information
trend_info = strategy.get_trend_info('AAPL')
print(f"Trend: {trend_info['trend']}")
print(f"Strength: {trend_info['strength']}")
```

## Benefits

1. **Avoid Downtrends**: Prevents entering positions during falling markets
2. **Improved Win Rate**: Only trades when market structure is favorable
3. **Risk Reduction**: Filters out high-risk setups
4. **Flexible**: Can be disabled or configured for different market conditions

## Performance Impact

**Expected Improvements:**
- Higher win rate (fewer losing trades in downtrends)
- Better risk-adjusted returns
- Reduced maximum drawdown
- Fewer total trades (more selective)

**Trade-offs:**
- May miss some profitable mean-reversion opportunities in downtrends
- Requires more historical data (200 bars minimum for full trend detection)
- Slightly slower execution due to additional calculations

## Configuration Recommendations

### Conservative (Strict Uptrend Only)
```python
use_trend=True
allow_flat_trend=False
```
Best for: Risk-averse traders, volatile markets

### Balanced (Default)
```python
use_trend=True
allow_flat_trend=True
```
Best for: Most market conditions, balanced risk/reward

### Aggressive (No Filter)
```python
use_trend=False
```
Best for: High-frequency trading, very stable markets

## Technical Details

### Trend Detection Algorithm
1. Calculate short MA (50 bars) and long MA (200 bars)
2. Calculate linear regression slope (50 bars)
3. Analyze higher highs/lower lows pattern (100 bars)
4. Combine signals with weighted voting:
   - MA trend: 2 points
   - LR slope: 1 point
   - HL pattern: 1 point
5. Classify:
   - Score ≥ 2: UP
   - Score ≤ -2: DOWN
   - Otherwise: FLAT

### Computational Complexity
- Time: O(n) per bar where n = max(short_window, long_window)
- Space: O(n) for price history storage
- Optimized with NumPy vectorization

## Future Enhancements

Potential improvements:
1. Add trend reversal detection
2. Implement trend strength-based position sizing
3. Add trend duration tracking
4. Support for multiple timeframe trend analysis
5. Machine learning-based trend classification

## Testing

To test the trend detection:
```python
from src.trends import TrendDetector

detector = TrendDetector()
for bar in historical_data:
    trend = detector.on_bar('AAPL', bar)
    print(f"Trend: {trend.value}, Strength: {detector.get_trend_strength('AAPL')}")
```

---
**Note**: Trend detection is enabled by default. Use `--no-trend` flag to disable if needed.