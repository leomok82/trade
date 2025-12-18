import pandas as pd
import numpy as np
from collections import defaultdict
from .visualizer import StrategyVisualizer

class BacktestEngine:
    """
    Event-driven backtesting engine.
    Iterates through data bars, executes strategy logic, and tracks performance.
    """
    def __init__(self, strategy, data, symbols, initial_capital=10000, enable_visualizer=True):
        self.strategy = strategy
        self.data = data
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.symbols = symbols
        self.positions = defaultdict(int) # {symbol: shares}
        self.last_prices = defaultdict(float) # {symbol: price}
        self.trades = []
        self.equity_curve = []
        
        # Initialize visualizer
        self.enable_visualizer = enable_visualizer
        self.visualizer = StrategyVisualizer(symbols, initial_capital) if enable_visualizer else None
    
    def run(self):
        """
        Executes the backtest simulation.
        Returns:
            pd.DataFrame: Equity curve.
        """
        # Ensure data is sorted by time to simulate correctly
        # Assuming data has MultiIndex (symbol, timestamp) or just timestamp
        # If it's MultiIndex, we might want to sort by timestamp level
        
        # Check if index is MultiIndex
        is_multi_index = isinstance(self.data.index, pd.MultiIndex)
        
        if is_multi_index:
            # Sort by timestamp (level 1 usually, but let's check names or assume level 1)
            # Alpaca-py usually returns (symbol, timestamp)
            # We want to iterate by timestamp, then symbol
            # So let's swap levels and sort
            if self.data.index.names[0] == 'symbol':
                 sorted_data = self.data.swaplevel(0, 1).sort_index()
            else:
                 sorted_data = self.data.sort_index()
        else:
            sorted_data = self.data.sort_index()

        for index, row in sorted_data.iterrows():
            # Determine symbol
            if is_multi_index:
                # index is (timestamp, symbol) after swap
                timestamp, symbol = index
            else:
                # If single index, we might need symbol from column or assume single symbol
                # But this engine is now multi-symbol capable.
                # If data is single symbol, we can just use self.symbols[0] or similar
                # For robustness, let's assume if not multi-index, it's a single symbol df
                symbol = self.symbols[0] if self.symbols else 'UNKNOWN'
                timestamp = index

            # Update last price for mark-to-market
            price = row['close']
            self.last_prices[symbol] = price

            # Execute strategy on current bar
            signal = self.strategy.on_bar(symbol, row)
            
            # Update visualizer before executing trades
            if self.visualizer:
                position_value = sum(self.positions[s] * self.last_prices[s] for s in self.positions)
                current_equity = self.capital + position_value
                self.visualizer.update(
                    timestamp=timestamp,
                    equity=current_equity,
                    cash=self.capital,
                    positions=dict(self.positions),
                    last_prices=dict(self.last_prices),
                    signal=signal,
                    symbol=symbol,
                    price=price
                )
            
            # Execute Trades
            if signal == 1 and self.positions[symbol] == 0: # Buy Signal
                
                allocation = self.initial_capital / (len(self.symbols)//2)
                # But we can only use what we have
                trade_amt = min(self.capital, allocation)
                
                shares = trade_amt // price
                if shares > 0:
                    self.positions[symbol] = shares
                    cost = shares * price
                    self.capital -= cost
                    self.trades.append({
                        'type': 'buy', 
                        'price': price, 
                        'date': timestamp, 
                        'symbol': symbol,
                        'shares': shares,
                        'cost': cost
                    })
            elif signal == -1 and self.positions[symbol] > 0: # Sell Signal
                shares = self.positions[symbol]
                proceeds = shares * price
                self.capital += proceeds
                self.trades.append({
                    'type': 'sell', 
                    'price': price, 
                    'date': timestamp, 
                    'symbol': symbol,
                    'shares': shares,
                    'proceeds': proceeds
                })
                self.positions[symbol] = 0
            
            # Mark to Market
            # Equity = Cash + Value of all positions
            position_value = sum(self.positions[s] * self.last_prices[s] for s in self.positions)
            current_equity = self.capital + position_value
            self.equity_curve.append({'timestamp': timestamp, 'equity': current_equity})
        
        # Create Equity Curve DataFrame
        self.equity_df = pd.DataFrame(self.equity_curve).set_index('timestamp')
        # Resample to daily or keep as is? Keep as is (minute/trade level)
        # But we might have duplicate timestamps if multiple symbols trade at same minute.
        # We should probably take the last equity value for each timestamp.
        self.equity_df = self.equity_df.groupby(level=0).last()
        
        return self.equity_df

    def get_trades(self):
        """Returns a DataFrame of all executed trades."""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)

    def get_stats(self):
        """Calculates and returns summary statistics."""
        if self.equity_df.empty:
            return {}

        equity = self.equity_df['equity']
        returns = equity.pct_change().dropna()
        
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital
        
        # Sharpe Ratio (assuming 252 trading days, risk-free rate 0 for simplicity)
        # If data is minute data, we need to scale appropriately.
        # Assuming minute data (252 * 390 minutes)
        # But returns are per step. Steps are irregular?
        # Let's resample to daily for Sharpe calculation to be standard
        daily_equity = equity.resample('D').last().dropna()
        daily_returns = daily_equity.pct_change().dropna()
        
        if daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Max Drawdown
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Win Rate (based on closed trades)
        trades_df = self.get_trades()
        win_rate = 0.0
        if not trades_df.empty:
            # Pair buy/sells to calculate trade PnL roughly
            # This is harder with multi-symbol. We need to group by symbol.
            wins = 0
            total_closed = 0
            
            for symbol in self.symbols:
                sym_trades = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()
                if sym_trades.empty: continue
                
                sells = sym_trades[sym_trades['type'] == 'sell']
                buys = sym_trades[sym_trades['type'] == 'buy']
                
                # Simple FIFO matching
                for i in range(len(sells)):
                    if i < len(buys):
                        pnl = sells.iloc[i]['proceeds'] - buys.iloc[i]['cost']
                        if pnl > 0: wins += 1
                        total_closed += 1
            
            win_rate = wins / total_closed if total_closed > 0 else 0.0

        return {
            "Total Return": f"{total_return:.2%}",
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown": f"{max_drawdown:.2%}",
            "Win Rate": f"{win_rate:.2%}",
            "Final Equity": f"${equity.iloc[-1]:.2f}",
            "Total Trades": len(trades_df)
        }
