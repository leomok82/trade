import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
import seaborn as sns

class StrategyVisualizer:
    """
    Visualizer class for tracking and plotting trading strategy metrics.
    Tracks trades, equity, positions, and provides comprehensive visualization.
    """
    
    def __init__(self, symbols, initial_capital=10000):
        """
        Initialize the visualizer.
        
        Args:
            symbols: List of symbols being traded
            initial_capital: Starting capital amount
        """
        self.symbols = symbols
        self.initial_capital = initial_capital
        
        # Data tracking
        self.timestamps = []
        self.equity_values = []
        self.cash_values = []
        self.position_values = []
        
        # Trade tracking
        self.buy_signals = defaultdict(list)  # {symbol: [(timestamp, price), ...]}
        self.sell_signals = defaultdict(list)  # {symbol: [(timestamp, price), ...]}
        
        # Price tracking for each symbol
        self.price_history = defaultdict(list)  # {symbol: [(timestamp, price), ...]}
        
        # Position tracking
        self.position_history = defaultdict(list)  # {symbol: [(timestamp, shares), ...]}
        
        # Metrics tracking
        self.returns = []
        self.drawdowns = []
        self.cumulative_pnl = []
        
    def update(self, timestamp, equity, cash, positions, last_prices, signal=None, symbol=None, price=None):
        """
        Update visualizer with current state.
        
        Args:
            timestamp: Current timestamp
            equity: Total equity (cash + positions)
            cash: Available cash
            positions: Dict of {symbol: shares}
            last_prices: Dict of {symbol: price}
            signal: Trading signal (1=buy, -1=sell, 0=hold)
            symbol: Symbol for the signal
            price: Price at which signal occurred
        """
        # Track equity curve
        self.timestamps.append(timestamp)
        self.equity_values.append(equity)
        self.cash_values.append(cash)
        
        # Calculate position value
        position_value = sum(positions.get(s, 0) * last_prices.get(s, 0) for s in self.symbols)
        self.position_values.append(position_value)
        
        # Track returns
        if len(self.equity_values) > 1:
            ret = (self.equity_values[-1] - self.equity_values[-2]) / self.equity_values[-2]
            self.returns.append(ret)
        
        # Track drawdown
        if self.equity_values:
            peak = max(self.equity_values)
            drawdown = (equity - peak) / peak
            self.drawdowns.append(drawdown)
        
        # Track cumulative PnL
        pnl = equity - self.initial_capital
        self.cumulative_pnl.append(pnl)
        
        # Track prices for all symbols
        for sym in self.symbols:
            if sym in last_prices:
                self.price_history[sym].append((timestamp, last_prices[sym]))
        
        # Track positions
        for sym in self.symbols:
            if sym in positions:
                self.position_history[sym].append((timestamp, positions[sym]))
        
        # Track signals
        if signal is not None and symbol is not None and price is not None:
            if signal == 1:  # Buy
                self.buy_signals[symbol].append((timestamp, price))
            elif signal == -1:  # Sell
                self.sell_signals[symbol].append((timestamp, price))
    
    def plot_cumulative_profit(self, figsize=(14, 8), save_path=None):
        """
        Plot cumulative profit/loss over time.
        
        Args:
            figsize: Figure size tuple
            save_path: Optional path to save the figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        if not self.timestamps:
            print("No data to plot")
            return
        
        # Plot cumulative PnL
        ax.plot(self.timestamps, self.cumulative_pnl, label='Cumulative P&L', linewidth=2, color='blue')
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        # Fill positive/negative areas
        ax.fill_between(self.timestamps, self.cumulative_pnl, 0, 
                        where=np.array(self.cumulative_pnl) >= 0, 
                        alpha=0.3, color='green', label='Profit')
        ax.fill_between(self.timestamps, self.cumulative_pnl, 0, 
                        where=np.array(self.cumulative_pnl) < 0, 
                        alpha=0.3, color='red', label='Loss')
        
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Cumulative P&L ($)', fontsize=12)
        ax.set_title('Cumulative Profit/Loss Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_equity_curve(self, figsize=(14, 8), save_path=None):
        """
        Plot equity curve with buy/sell signals.
        
        Args:
            figsize: Figure size tuple
            save_path: Optional path to save the figure
        """
        if not self.timestamps:
            print("No data to plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])
        
        # Plot equity curve
        ax1.plot(self.timestamps, self.equity_values, label='Total Equity', linewidth=2, color='blue')
        ax1.plot(self.timestamps, self.cash_values, label='Cash', linewidth=1, alpha=0.7, color='green')
        ax1.plot(self.timestamps, self.position_values, label='Position Value', linewidth=1, alpha=0.7, color='orange')
        ax1.axhline(y=self.initial_capital, color='red', linestyle='--', alpha=0.5, label='Initial Capital')
        
        ax1.set_ylabel('Value ($)', fontsize=12)
        ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Plot drawdown
        ax2.fill_between(self.timestamps, self.drawdowns, 0, alpha=0.5, color='red')
        ax2.plot(self.timestamps, self.drawdowns, linewidth=1, color='darkred')
        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.set_title('Drawdown', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Format y-axis as percentage
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_trades(self, symbol=None, figsize=(14, 10), save_path=None):
        """
        Plot price history with buy/sell signals for each symbol.
        
        Args:
            symbol: Specific symbol to plot (None = all symbols)
            figsize: Figure size tuple
            save_path: Optional path to save the figure
        """
        symbols_to_plot = [symbol] if symbol else self.symbols
        n_symbols = len(symbols_to_plot)
        
        if n_symbols == 0:
            print("No symbols to plot")
            return
        
        fig, axes = plt.subplots(n_symbols, 1, figsize=figsize, squeeze=False)
        axes = axes.flatten()
        
        for idx, sym in enumerate(symbols_to_plot):
            ax = axes[idx]
            
            # Get price history
            if sym not in self.price_history or not self.price_history[sym]:
                ax.text(0.5, 0.5, f'No data for {sym}', ha='center', va='center', transform=ax.transAxes)
                continue
            
            timestamps, prices = zip(*self.price_history[sym])
            
            # Plot price
            ax.plot(timestamps, prices, label=f'{sym} Price', linewidth=1.5, color='black', alpha=0.7)
            
            # Plot buy signals
            if sym in self.buy_signals and self.buy_signals[sym]:
                buy_times, buy_prices = zip(*self.buy_signals[sym])
                ax.scatter(buy_times, buy_prices, color='green', marker='^', s=100, 
                          label='Buy', zorder=5, edgecolors='darkgreen', linewidths=1.5)
            
            # Plot sell signals
            if sym in self.sell_signals and self.sell_signals[sym]:
                sell_times, sell_prices = zip(*self.sell_signals[sym])
                ax.scatter(sell_times, sell_prices, color='red', marker='v', s=100, 
                          label='Sell', zorder=5, edgecolors='darkred', linewidths=1.5)
            
            ax.set_ylabel('Price ($)', fontsize=11)
            ax.set_title(f'{sym} - Price with Trade Signals', fontsize=12, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
        
        axes[-1].set_xlabel('Time', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_positions(self, figsize=(14, 8), save_path=None):
        """
        Plot position sizes over time for each symbol.
        
        Args:
            figsize: Figure size tuple
            save_path: Optional path to save the figure
        """
        if not any(self.position_history.values()):
            print("No position data to plot")
            return
        
        fig, ax = plt.subplots(figsize=figsize)
        
        for sym in self.symbols:
            if sym in self.position_history and self.position_history[sym]:
                timestamps, positions = zip(*self.position_history[sym])
                ax.plot(timestamps, positions, label=sym, linewidth=2, marker='o', markersize=3)
        
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Position Size (shares)', fontsize=12)
        ax.set_title('Position Sizes Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_all(self, figsize=(16, 12), save_path=None):
        """
        Create a comprehensive dashboard with all visualizations.
        
        Args:
            figsize: Figure size tuple
            save_path: Optional path to save the figure
        """
        if not self.timestamps:
            print("No data to plot")
            return
        
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        # 1. Equity Curve
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(self.timestamps, self.equity_values, label='Total Equity', linewidth=2, color='blue')
        ax1.axhline(y=self.initial_capital, color='red', linestyle='--', alpha=0.5, label='Initial Capital')
        ax1.set_ylabel('Value ($)', fontsize=11)
        ax1.set_title('Equity Curve', fontsize=12, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # 2. Cumulative P&L
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(self.timestamps, self.cumulative_pnl, linewidth=2, color='blue')
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        ax2.fill_between(self.timestamps, self.cumulative_pnl, 0, 
                        where=np.array(self.cumulative_pnl) >= 0, 
                        alpha=0.3, color='green')
        ax2.fill_between(self.timestamps, self.cumulative_pnl, 0, 
                        where=np.array(self.cumulative_pnl) < 0, 
                        alpha=0.3, color='red')
        ax2.set_ylabel('P&L ($)', fontsize=11)
        ax2.set_title('Cumulative P&L', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # 3. Drawdown
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.fill_between(self.timestamps, self.drawdowns, 0, alpha=0.5, color='red')
        ax3.plot(self.timestamps, self.drawdowns, linewidth=1, color='darkred')
        ax3.set_ylabel('Drawdown (%)', fontsize=11)
        ax3.set_title('Drawdown', fontsize=12, fontweight='bold')
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
        ax3.grid(True, alpha=0.3)
        
        # 4. Trade Distribution (Buy/Sell counts)
        ax4 = fig.add_subplot(gs[2, 0])
        buy_counts = [len(self.buy_signals.get(sym, [])) for sym in self.symbols]
        sell_counts = [len(self.sell_signals.get(sym, [])) for sym in self.symbols]
        x = np.arange(len(self.symbols))
        width = 0.35
        ax4.bar(x - width/2, buy_counts, width, label='Buys', color='green', alpha=0.7)
        ax4.bar(x + width/2, sell_counts, width, label='Sells', color='red', alpha=0.7)
        ax4.set_ylabel('Count', fontsize=11)
        ax4.set_title('Trade Distribution by Symbol', fontsize=12, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(self.symbols, rotation=45, ha='right')
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 5. Returns Distribution
        ax5 = fig.add_subplot(gs[2, 1])
        if self.returns:
            ax5.hist(self.returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
            ax5.axvline(x=0, color='red', linestyle='--', alpha=0.5)
            ax5.set_xlabel('Return', fontsize=11)
            ax5.set_ylabel('Frequency', fontsize=11)
            ax5.set_title('Returns Distribution', fontsize=12, fontweight='bold')
            ax5.grid(True, alpha=0.3, axis='y')
        
        plt.suptitle('Trading Strategy Performance Dashboard', fontsize=16, fontweight='bold', y=0.995)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def get_summary_stats(self):
        """
        Calculate and return summary statistics.
        
        Returns:
            dict: Dictionary of performance metrics
        """
        if not self.equity_values:
            return {}
        
        total_return = (self.equity_values[-1] - self.initial_capital) / self.initial_capital
        
        # Calculate Sharpe ratio (annualized)
        if len(self.returns) > 1:
            mean_return = np.mean(self.returns)
            std_return = np.std(self.returns)
            sharpe = (mean_return / std_return) * np.sqrt(252 * 390) if std_return > 0 else 0  # Assuming minute data
        else:
            sharpe = 0
        
        max_drawdown = min(self.drawdowns) if self.drawdowns else 0
        
        total_trades = sum(len(self.buy_signals[sym]) for sym in self.symbols)
        
        return {
            'Initial Capital': f'${self.initial_capital:,.2f}',
            'Final Equity': f'${self.equity_values[-1]:,.2f}',
            'Total Return': f'{total_return:.2%}',
            'Total P&L': f'${self.cumulative_pnl[-1]:,.2f}',
            'Max Drawdown': f'{max_drawdown:.2%}',
            'Sharpe Ratio': f'{sharpe:.2f}',
            'Total Trades': total_trades,
            'Avg Return per Trade': f'{np.mean(self.returns):.4%}' if self.returns else 'N/A'
        }
    
    def print_summary(self):
        """Print summary statistics to console."""
        stats = self.get_summary_stats()
        print("\n" + "="*50)
        print("STRATEGY PERFORMANCE SUMMARY")
        print("="*50)
        for key, value in stats.items():
            print(f"{key:.<30} {value}")
        print("="*50 + "\n")

# Made with Bob
