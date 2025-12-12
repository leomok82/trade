import numpy as np
import pandas as pd

class MonteCarloSimulator:
    def __init__(self, returns, num_simulations=1000, num_days=252):
        self.returns = returns
        self.num_simulations = num_simulations
        self.num_days = num_days

    def run(self):
        mean = self.returns.mean()
        std = self.returns.std()
        
        simulations = np.random.normal(mean, std, (self.num_days, self.num_simulations))
        cumulative_returns = (1 + simulations).cumprod(axis=0)
        
        return pd.DataFrame(cumulative_returns)
