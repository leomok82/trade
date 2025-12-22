import pandas as pd
import numpy as np
from collections import defaultdict
from .visualizer import StrategyVisualizer
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

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
        
        self.strategy = strategy
        self.data = data
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.symbols = symbols
        self.trades = []
        self.equity_curve = []
        


        
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
        
        # Run each symbol in its own worker; each worker returns its own trades and equity points
        all_equity_points = []
        all_trades = []

        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            futures = []
            for symbol in symbols:
                symbol_data = symbol_data_dict[symbol]
                futures.append(executor.submit(self._worker, symbol, symbol_data))

            # Collect results from workers
            for future in futures:
                trades, equity_points = future.result()
                if trades:
                    all_trades.extend(trades)
                if equity_points:
                    all_equity_points.extend(equity_points)

        # Consolidate equity: sum per timestamp across workers
        if all_equity_points:
            equity_df = pd.DataFrame(all_equity_points).set_index('timestamp')
            # sum equities across workers for same timestamp
            equity_df = equity_df.groupby(level=0).sum()
            # store
            self.equity_df = equity_df.sort_index()
        else:
            self.equity_df = pd.DataFrame()

        # Consolidate and sort trades chronologically
        self.trades = sorted(all_trades, key=lambda t: t.get('date'))

        return self.equity_df

    def _worker(self, symbol, symbol_data):
        """
        Worker processes all bars for a single symbol and returns its trades and equity points.
        No shared state is modified.
        Returns:
            (trades_list, equity_points_list)
        """
        state = LiveState()
        trades = []
        shares = 0
        equity_points = []

        # allocate capital per worker (split initial capital evenly)
        per_worker_capital = float(self.initial_capital) / max(1, len(self.symbols))
        local_capital = per_worker_capital

        for timestamp, row in symbol_data.iterrows():
            price = row['close']
            signal = self.strategy.on_bar(row, state)

            if signal == 1:
                # Buy using available local capital
                trade_amt = local_capital
                if trade_amt > 0:
                    shares = trade_amt / price
                    local_capital -= trade_amt

                    trades.append({
                        'type': 'buy',
                        'price': price,
                        'date': timestamp,
                        'symbol': symbol,
                        'shares': shares,
                        'cost': trade_amt
                    })

            elif signal == -1:
                if shares > 0:
                    proceeds = shares * price
                    local_capital += proceeds

                    trades.append({
                        'type': 'sell',
                        'price': price,
                        'date': timestamp,
                        'symbol': symbol,
                        'shares': shares,
                        'proceeds': proceeds
                    })
                    shares = 0

            # mark-to-market equity: cash + holdings value
            equity = local_capital + shares * price
            equity_points.append({'timestamp': timestamp, 'equity': equity})

        return trades, equity_points
    


        
    def get_trades(self):
        """Returns a DataFrame of all executed trades."""
        if not self.trades:
            return pd.DataFrame()
        df = pd.DataFrame(self.trades)
        # ensure chronological order
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)
        return df

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
