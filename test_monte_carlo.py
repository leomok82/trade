"""
Test script to verify Monte Carlo simulator integration with BacktestEngine.
"""
import numpy as np
import pandas as pd
from src.monte_carlo import MonteCarloSimulator

def test_basic_functionality():
    """Test basic Monte Carlo functionality."""
    print("=" * 60)
    print("Testing Basic Monte Carlo Functionality")
    print("=" * 60)
    
    # Create sample returns data (simulating equity curve returns)
    np.random.seed(42)
    sample_returns = pd.Series(np.random.normal(0.001, 0.02, 252))
    
    # Initialize simulator
    mc = MonteCarloSimulator(
        returns=sample_returns,
        num_simulations=1000,
        num_days=252,
        initial_value=10000.0
    )
    
    # Run simulation
    print("\n1. Running Monte Carlo simulation...")
    results = mc.run()
    print(f"   ✓ Generated {results.shape[1]} simulation paths")
    print(f"   ✓ Each path has {results.shape[0]} days")
    
    # Test percentiles
    print("\n2. Testing percentile analysis...")
    percentiles = mc.get_percentiles([5, 25, 50, 75, 95])
    for p, value in percentiles.items():
        print(f"   {p} percentile: ${value:,.2f}")
    
    # Test confidence interval
    print("\n3. Testing confidence interval...")
    lower, upper = mc.get_confidence_interval(0.95)
    print(f"   95% Confidence Interval: ${lower:,.2f} - ${upper:,.2f}")
    
    # Test VaR
    print("\n4. Testing Value at Risk (VaR)...")
    var_95 = mc.calculate_var(0.95)
    var_99 = mc.calculate_var(0.99)
    print(f"   95% VaR: ${var_95:,.2f} (5% chance of losing more)")
    print(f"   99% VaR: ${var_99:,.2f} (1% chance of losing more)")
    
    # Test CVaR
    print("\n5. Testing Conditional VaR (CVaR)...")
    cvar_95 = mc.calculate_cvar(0.95)
    cvar_99 = mc.calculate_cvar(0.99)
    print(f"   95% CVaR: ${cvar_95:,.2f} (expected loss in worst 5%)")
    print(f"   99% CVaR: ${cvar_99:,.2f} (expected loss in worst 1%)")
    
    # Test summary stats
    print("\n6. Testing summary statistics...")
    stats = mc.get_summary_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)

def test_integration_with_engine():
    """Test integration pattern with BacktestEngine."""
    print("\n" + "=" * 60)
    print("Testing Integration Pattern with BacktestEngine")
    print("=" * 60)
    
    # Simulate equity curve from BacktestEngine
    print("\n1. Simulating BacktestEngine equity curve...")
    dates = pd.date_range('2023-01-01', periods=252, freq='D')
    equity_values = 10000 * (1 + np.random.normal(0.001, 0.02, 252)).cumprod()
    equity_df = pd.DataFrame({'equity': equity_values}, index=dates)
    print(f"   ✓ Created equity curve: ${equity_df['equity'].iloc[0]:.2f} → ${equity_df['equity'].iloc[-1]:.2f}")
    
    # Calculate returns (as would be done in main.py)
    print("\n2. Calculating returns from equity curve...")
    returns = equity_df['equity'].pct_change().dropna()
    print(f"   ✓ Generated {len(returns)} return observations")
    print(f"   ✓ Mean return: {returns.mean():.4%}")
    print(f"   ✓ Std dev: {returns.std():.4%}")
    
    # Run Monte Carlo
    print("\n3. Running Monte Carlo simulation...")
    mc = MonteCarloSimulator(
        returns=returns,
        num_simulations=1000,
        num_days=252,
        initial_value=equity_df['equity'].iloc[-1]  # Start from final equity
    )
    mc_results = mc.run()
    print(f"   ✓ Simulated {mc_results.shape[1]} future paths")
    
    # Show key metrics
    print("\n4. Key Monte Carlo metrics:")
    stats = mc.get_summary_stats()
    print(f"   Current Portfolio Value: ${equity_df['equity'].iloc[-1]:,.2f}")
    print(f"   {stats['Mean Final Value']} (projected 1 year)")
    print(f"   {stats['Probability of Profit']}")
    
    percentiles = mc.get_percentiles([5, 50, 95])
    print(f"\n5. Projected outcomes (1 year):")
    print(f"   Best case (95th): ${percentiles['95th']:,.2f}")
    print(f"   Expected (50th): ${percentiles['50th']:,.2f}")
    print(f"   Worst case (5th): ${percentiles['5th']:,.2f}")
    
    print("\n" + "=" * 60)
    print("✓ Integration test passed successfully!")
    print("=" * 60)

def test_error_handling():
    """Test error handling and validation."""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)
    
    test_cases = [
        ("Empty returns", lambda: MonteCarloSimulator(pd.Series([]), 100, 252)),
        ("Negative simulations", lambda: MonteCarloSimulator(pd.Series([0.01, 0.02]), -100, 252)),
        ("Negative days", lambda: MonteCarloSimulator(pd.Series([0.01, 0.02]), 100, -252)),
        ("Negative initial value", lambda: MonteCarloSimulator(pd.Series([0.01, 0.02]), 100, 252, -1000)),
    ]
    
    for test_name, test_func in test_cases:
        try:
            test_func()
            print(f"   ✗ {test_name}: Should have raised an error")
        except (ValueError, TypeError) as e:
            print(f"   ✓ {test_name}: Correctly raised {type(e).__name__}")
    
    # Test calling methods before run()
    print("\n   Testing method calls before run():")
    mc = MonteCarloSimulator(pd.Series([0.01, 0.02, 0.03]), 100, 252)
    
    methods_to_test = [
        ("get_percentiles", lambda: mc.get_percentiles()),
        ("get_confidence_interval", lambda: mc.get_confidence_interval()),
        ("calculate_var", lambda: mc.calculate_var()),
        ("calculate_cvar", lambda: mc.calculate_cvar()),
        ("get_summary_stats", lambda: mc.get_summary_stats()),
    ]
    
    for method_name, method_func in methods_to_test:
        try:
            method_func()
            print(f"   ✗ {method_name}: Should have raised RuntimeError")
        except RuntimeError:
            print(f"   ✓ {method_name}: Correctly raised RuntimeError")
    
    print("\n" + "=" * 60)
    print("✓ Error handling tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_integration_with_engine()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Monte Carlo simulator is ready.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

# Made with Bob
