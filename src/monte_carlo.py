import numpy as np
import pandas as pd
from enum import Enum

class RegimeType(Enum):
    """Market regime types for regime-aware simulations"""
    LOW_VOL = "low_volatility"
    NORMAL = "normal"
    HIGH_VOL = "high_volatility"

class MonteCarloSimulator:
    """
    Monte Carlo simulator for portfolio projections and risk analysis.
    
    Simulates future portfolio paths based on historical returns distribution,
    with optional regime-aware modeling for more realistic scenarios.
    """
    
    def __init__(self, returns, num_simulations=1000, num_days=252, initial_value=1.0,
                 regime_aware=True, volatility_data=None):
        """
        Initialize Monte Carlo simulator.
        
        Args:
            returns: pandas Series of historical returns (e.g., from equity.pct_change())
            num_simulations: Number of simulation paths to generate
            num_days: Number of days to project forward
            initial_value: Starting value for simulations (default 1.0 for normalized returns)
            regime_aware: Enable regime-based simulation (default: False)
            volatility_data: pandas Series of historical volatility for regime detection (optional)
        """
        # Input validation
        if not isinstance(returns, (pd.Series, np.ndarray)):
            raise TypeError("returns must be a pandas Series or numpy array")
        
        if isinstance(returns, pd.Series):
            returns = returns.dropna()
        
        if len(returns) == 0:
            raise ValueError("returns cannot be empty")
        
        if num_simulations <= 0 or num_days <= 0:
            raise ValueError("num_simulations and num_days must be positive integers")
        
        if initial_value <= 0:
            raise ValueError("initial_value must be positive")
        
        self.returns = returns
        self.num_simulations = int(num_simulations)
        self.num_days = int(num_days)
        self.initial_value = initial_value
        self.regime_aware = regime_aware
        self.volatility_data = volatility_data
        
        # Storage for simulation results
        self.simulations = None
        self.final_values = None
        
        # Regime-specific statistics
        self.regime_stats = None
        if regime_aware and volatility_data is not None:
            self._calculate_regime_stats()
        
    def _calculate_regime_stats(self):
        """Calculate regime-specific return statistics."""
        if self.volatility_data is None or len(self.volatility_data) != len(self.returns):
            return
        
        # Classify regimes based on volatility percentiles
        vol_25 = np.percentile(self.volatility_data, 25)
        vol_75 = np.percentile(self.volatility_data, 75)
        
        # Separate returns by regime
        low_vol_mask = self.volatility_data < vol_25
        normal_vol_mask = (self.volatility_data >= vol_25) & (self.volatility_data < vol_75)
        high_vol_mask = self.volatility_data >= vol_75
        
        self.regime_stats = {
            RegimeType.LOW_VOL: {
                'mean': self.returns[low_vol_mask].mean() if low_vol_mask.sum() > 0 else self.returns.mean(),
                'std': self.returns[low_vol_mask].std() if low_vol_mask.sum() > 0 else self.returns.std(),
                'probability': low_vol_mask.sum() / len(self.returns)
            },
            RegimeType.NORMAL: {
                'mean': self.returns[normal_vol_mask].mean() if normal_vol_mask.sum() > 0 else self.returns.mean(),
                'std': self.returns[normal_vol_mask].std() if normal_vol_mask.sum() > 0 else self.returns.std(),
                'probability': normal_vol_mask.sum() / len(self.returns)
            },
            RegimeType.HIGH_VOL: {
                'mean': self.returns[high_vol_mask].mean() if high_vol_mask.sum() > 0 else self.returns.mean(),
                'std': self.returns[high_vol_mask].std() if high_vol_mask.sum() > 0 else self.returns.std(),
                'probability': high_vol_mask.sum() / len(self.returns)
            }
        }
    
    def run(self):
        """
        Execute Monte Carlo simulation.
        
        Generates random return paths based on historical mean and standard deviation.
        If regime_aware is enabled, simulates regime transitions and uses regime-specific statistics.
        
        Returns:
            pd.DataFrame: Simulation paths with shape (num_days, num_simulations)
        """
        if self.regime_aware and self.regime_stats is not None:
            # Regime-aware simulation
            self.simulations = self._run_regime_aware()
        else:
            # Standard simulation
            self.simulations = self._run_standard()
        
        # Store final values for risk analysis
        self.final_values = self.simulations[-1, :]
        
        return pd.DataFrame(self.simulations)
    
    def _run_standard(self):
        """Standard Monte Carlo simulation without regime awareness."""
        # Calculate statistics from historical returns
        mean = self.returns.mean()
        std = self.returns.std()
        
        # Generate random returns using normal distribution
        # Shape: (num_days, num_simulations)
        random_returns = np.random.normal(mean, std, (self.num_days, self.num_simulations))
        
        # Calculate cumulative returns (compound growth)
        cumulative_returns = (1 + random_returns).cumprod(axis=0)
        
        # Scale by initial value
        return cumulative_returns * self.initial_value
    
    def _run_regime_aware(self):
        """Regime-aware Monte Carlo simulation with regime switching."""
        if self.regime_stats is None:
            return self._run_standard()
        
        simulations = np.zeros((self.num_days, self.num_simulations))
        
        # Initialize with starting value
        simulations[0, :] = self.initial_value
        
        # Get regime probabilities for transitions
        regimes = list(self.regime_stats.keys())
        regime_probs = [self.regime_stats[r]['probability'] for r in regimes]
        regime_indices = list(range(len(regimes)))
        
        for sim in range(self.num_simulations):
            current_value = self.initial_value
            
            for day in range(self.num_days):
                # Select regime based on historical probabilities
                regime_idx = np.random.choice(regime_indices, p=regime_probs)
                regime = regimes[regime_idx]
                
                # Get regime-specific statistics
                mean = self.regime_stats[regime]['mean']
                std = self.regime_stats[regime]['std']
                
                # Generate return for this day
                daily_return = np.random.normal(mean, std)
                
                # Update value
                current_value *= (1 + daily_return)
                simulations[day, sim] = current_value
        
        return simulations
    
    def get_percentiles(self, percentiles=[5, 25, 50, 75, 95]):
        """
        Calculate percentile outcomes across all simulation paths.
        
        Args:
            percentiles: List of percentile values to calculate (0-100)
            
        Returns:
            dict: Dictionary mapping percentile to final portfolio value
        """
        if self.simulations is None or self.final_values is None:
            raise RuntimeError("Must call run() before calculating percentiles")
        
        result = {}
        for p in percentiles:
            if not 0 <= p <= 100:
                raise ValueError(f"Percentile {p} must be between 0 and 100")
            result[f"{p}th"] = float(np.percentile(self.final_values, p))
        
        return result
    
    def get_confidence_interval(self, confidence=0.95):
        """
        Calculate confidence interval for final portfolio value.
        
        Args:
            confidence: Confidence level (e.g., 0.95 for 95% confidence)
            
        Returns:
            tuple: (lower_bound, upper_bound) of confidence interval
        """
        if self.simulations is None or self.final_values is None:
            raise RuntimeError("Must call run() before calculating confidence interval")
        
        if not 0 < confidence < 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        alpha = 1 - confidence
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = float(np.percentile(self.final_values, lower_percentile))
        upper_bound = float(np.percentile(self.final_values, upper_percentile))
        
        return (lower_bound, upper_bound)
    
    def calculate_var(self, confidence=0.95):
        """
        Calculate Value at Risk (VaR).
        
        VaR represents the maximum expected loss at a given confidence level.
        For example, 95% VaR means there's a 5% chance of losing more than this amount.
        
        Args:
            confidence: Confidence level (e.g., 0.95 for 95% VaR)
            
        Returns:
            float: Value at Risk (positive number represents potential loss)
        """
        if self.simulations is None or self.final_values is None:
            raise RuntimeError("Must call run() before calculating VaR")
        
        if not 0 < confidence < 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        # VaR is the loss at the (1-confidence) percentile
        # We calculate loss relative to initial value
        percentile = (1 - confidence) * 100
        var_value = float(np.percentile(self.final_values, percentile))
        
        # Return as loss (positive number)
        var_loss = self.initial_value - var_value
        
        return max(0.0, var_loss)  # VaR cannot be negative
    
    def calculate_cvar(self, confidence=0.95):
        """
        Calculate Conditional Value at Risk (CVaR), also known as Expected Shortfall.
        
        CVaR is the expected loss given that the loss exceeds VaR.
        It represents the average of the worst-case scenarios beyond the VaR threshold.
        
        Args:
            confidence: Confidence level (e.g., 0.95 for 95% CVaR)
            
        Returns:
            float: Conditional VaR (positive number represents expected loss in tail scenarios)
        """
        if self.simulations is None or self.final_values is None:
            raise RuntimeError("Must call run() before calculating CVaR")
        
        if not 0 < confidence < 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        # Find the VaR threshold
        percentile = (1 - confidence) * 100
        var_threshold = float(np.percentile(self.final_values, percentile))
        
        # CVaR is the average of all values below VaR threshold
        tail_values = self.final_values[self.final_values <= var_threshold]
        
        if len(tail_values) == 0:
            return 0.0
        
        cvar_value = float(np.mean(tail_values))
        
        # Return as loss (positive number)
        cvar_loss = self.initial_value - cvar_value
        
        return max(0.0, cvar_loss)
    
    def get_summary_stats(self):
        """
        Calculate summary statistics of simulation outcomes.
        
        Returns:
            dict: Dictionary containing mean, median, std, min, max, and return metrics
        """
        if self.simulations is None or self.final_values is None:
            raise RuntimeError("Must call run() before calculating summary statistics")
        
        mean_final = float(np.mean(self.final_values))
        median_final = float(np.median(self.final_values))
        std_final = float(np.std(self.final_values))
        min_final = float(np.min(self.final_values))
        max_final = float(np.max(self.final_values))
        
        # Calculate return metrics
        mean_return = (mean_final - self.initial_value) / self.initial_value
        median_return = (median_final - self.initial_value) / self.initial_value
        best_return = (max_final - self.initial_value) / self.initial_value
        worst_return = (min_final - self.initial_value) / self.initial_value
        
        # Probability of profit
        prob_profit = float(np.sum(self.final_values > self.initial_value)) / len(self.final_values)
        
        return {
            "Mean Final Value": f"${mean_final:.2f}",
            "Median Final Value": f"${median_final:.2f}",
            "Std Dev": f"${std_final:.2f}",
            "Min Value": f"${min_final:.2f}",
            "Max Value": f"${max_final:.2f}",
            "Mean Return": f"{mean_return:.2%}",
            "Median Return": f"{median_return:.2%}",
            "Best Case Return": f"{best_return:.2%}",
            "Worst Case Return": f"{worst_return:.2%}",
            "Probability of Profit": f"{prob_profit:.2%}",
            "Number of Simulations": self.num_simulations,
            "Projection Days": self.num_days
        }

# Made with Bob
