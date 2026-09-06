import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
data_client = StockHistoricalDataClient(os.environ.get("ALPACA_API_KEY"), 
                                        os.environ.get("ALPACA_SECRET_KEY"))

target_stock = "SPY"

print(f"Fetching 1 year of historical data for {target_stock}...")
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

request_params = StockBarsRequest(
    symbol_or_symbols=target_stock,
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)
bars = data_client.get_stock_bars(request_params).df
close_prices = bars.xs(target_stock, level='symbol')['close']
log_returns = np.log(close_prices / close_prices.shift(1))

# 1. Define the Parameter Grid
windows = [5, 10, 15, 20, 30, 50]
z_thresholds = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5]

results = []

print("Running Grid Search Optimization...")

# 2. Iterate through every combination
for w in windows:
    # Calculate moving averages and volatility for this specific window
    rolling_mean = log_returns.rolling(window=w).mean()
    rolling_vol = log_returns.rolling(window=w).std()
    z_scores = (log_returns - rolling_mean) / rolling_vol
    
    for t in z_thresholds:
        # Apply the execution logic for this specific threshold
        conditions = [z_scores < -t, z_scores > t]
        choices = [1, -1]
        
        positions = np.select(conditions, choices, default=0)
        positions_series = pd.Series(positions, index=close_prices.index)
        
        # Shift positions to prevent look-ahead bias
        strategy_log_returns = positions_series.shift(1) * log_returns
        algo_return = (np.exp(strategy_log_returns.sum()) - 1) * 100
        
        # Store the results
        results.append({
            'Window': w, 
            'Z-Threshold': t, 
            'Return (%)': round(algo_return, 2)
        })

# 3. Analyze the Results
results_df = pd.DataFrame(results)

# Calculate Buy & Hold for comparison
buy_and_hold = (np.exp(log_returns.sum()) - 1) * 100

print("-" * 40)
print(f"Baseline Buy & Hold Return: {buy_and_hold:.2f}%")
print("-" * 40)
print("Top 5 Parameter Combinations:")
# Sort by highest return and print the top 5
print(results_df.sort_values(by='Return (%)', ascending=False).head(5))