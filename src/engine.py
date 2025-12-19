import pandas as pd
import numpy as np
from collections import defaultdict
from .visualizer import StrategyVisualizer
from dataclasses import dataclass, field

@dataclass
class LiveState:
    history: list[float] = field(default_factory=list)
    entry_mean: float = 0.0
    entry_std: float = 0.0
    pos: int = 0
    entry_price: float = 0.0
    cooldown: int = 0
    shares: int = 0          # add this, see next section


class BacktestEngine:
    """
    Multithreaded event-driven backtesting engine.
    Each symbol runs in its own thread, synchronized only when capital changes.
    """
    def __init__(self, strategy, data, symbols, initial_capital=10000, enable_visualizer=True):
        import threading
        
        self.strategy = strategy
        self.data = data
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.symbols = symbols
        self.trades = []
        self.equity_curve = []
        
        # Thread synchronization primitives
        self.capital_lock = threading.Lock()
        self.trades_lock = threading.Lock()
        self.equity_lock = threading.Lock()
        
        # Condition variable for capital changes
        self.capital_changed = threading.Condition(self.capital_lock)
        self.active_threads = 0
        self.threads_lock = threading.Lock()
        
        # Initialize visualizer
        self.enable_visualizer = enable_visualizer
        self.visualizer = StrategyVisualizer(symbols, initial_capital) if enable_visualizer else None
    
    def run(self):
        """
        Executes the backtest simulation using multiple threads.
        Each thread processes one symbol independently, synchronizing only on capital changes.
        Returns:
            pd.DataFrame: Equity curve.
        """
        import threading
        
        # Ensure data is sorted by time to simulate correctly
        is_multi_index = isinstance(self.data.index, pd.MultiIndex)
        
        if is_multi_index:
            sorted_data = self.data.reset_index().set_index('timestamp').sort_index()
        else:
            sorted_data = self.data.sort_index()
            # Add symbol column if not present
            if 'symbol' not in sorted_data.columns:
                sorted_data['symbol'] = self.symbols[0] if self.symbols else 'UNKNOWN'

        symbols = sorted_data['symbol'].unique()
        
        # Create symbol-specific data
        symbol_data_dict = {}
        
        for symbol in symbols:
            symbol_data_dict[symbol] = sorted_data[sorted_data['symbol'] == symbol].copy()
        
        # Create and start threads
        threads = []
        with self.threads_lock:
            self.active_threads = len(symbols)
        
        for symbol in symbols:
            thread = threading.Thread(
                target=self._worker,
                args=(symbol, symbol_data_dict[symbol])
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        # Create Equity Curve DataFrame
        if self.equity_curve:
            self.equity_df = pd.DataFrame(self.equity_curve).set_index('timestamp')
            self.equity_df = self.equity_df.groupby(level=0).last()
        else:
            self.equity_df = pd.DataFrame()
        
        return self.equity_df

    def _worker(self, symbol, symbol_data):
        """
        Worker function to process all bars for a single symbol.
        Only synchronizes when capital is being modified (trades).
        """
        state =  LiveState()
        for timestamp, row in symbol_data.iterrows():
            # Update last price for mark-to-market
            price = row['close']
            
            # Execute strategy on current bar
            signal = self.strategy.on_bar(row, state)
            
            
            # Execute Trades - only lock capital when actually trading
            if signal == 1:
            
                allocation = self.initial_capital / (len(self.symbols) // 2) if len(self.symbols) > 1 else self.initial_capital
                
                # Lock capital for thread-safe access - WAIT HERE if needed
                with self.capital_lock:
                    trade_amt = min(self.capital, allocation)
                    
                    self.capital -= trade_amt
                    shares = trade_amt / price
                                                
                    # Record trade
                    with self.trades_lock:
                        self.trades.append({
                            'type': 'buy',
                            'price': price,
                            'date': timestamp,
                            'symbol': symbol,
                            'shares': shares,
                            'cost': trade_amt
                        })
                    
            
            elif signal == -1:  # Sell Signal

                proceeds = state.shares * price
                
                # Lock capital for thread-safe access - WAIT HERE if needed
                with self.capital_lock:
                    self.capital += proceeds

                    
                    # Record trade
                    with self.trades_lock:
                        self.trades.append({
                            'type': 'sell',
                            'price': price,
                            'date': timestamp,
                            'symbol': symbol,
                            'shares': state.shares,
                            'proceeds': proceeds
                        })
                    
            
            # Record equity at this timestamp (no lock needed for reading if we're careful)
            with self.capital_lock:
                with self.equity_lock:
                    self.equity_curve.append({'timestamp': timestamp, 'equity': self.capital})
    
        # Thread finished
        with self.threads_lock:
            self.active_threads -= 1

        
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
