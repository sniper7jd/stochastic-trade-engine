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

# Define your variable here
target_stock = "SPY" # Let's test the broader market index

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

# Update the multi-index extraction to use the variable
close_prices = bars.xs(target_stock, level='symbol')['close']

print("Crunching mathematical models...")
# 1. Log Returns & Volatility
log_returns = np.log(close_prices / close_prices.shift(1))
rolling_mean = log_returns.rolling(window=20).mean()
rolling_vol = log_returns.rolling(window=20).std()

# 2. Vectorized Z-Scores (applied to the whole dataset instantly)
z_scores = (log_returns - rolling_mean) / rolling_vol

# 3. Generate Target Positions
# 1 = Long (Buy), -1 = Short (Sell), 0 = Neutral (Cash)
conditions = [
    z_scores < -2.0,  # Statistically oversold
    z_scores > 2.0    # Statistically overbought
]
choices = [1, -1]
# np.select applies these rules to every row simultaneously
positions = np.select(conditions, choices, default=0)
positions_series = pd.Series(positions, index=close_prices.index)

# 4. Calculate Returns & Prevent Look-Ahead Bias
# We MUST shift the position by 1 day. If the signal fires based on today's close, 
# we can only capture tomorrow's return. 
strategy_log_returns = positions_series.shift(1) * log_returns

# 5. Performance Evaluation
# Convert the sum of log returns back to arithmetic returns to see real percentages
buy_and_hold_return = (np.exp(log_returns.sum()) - 1) * 100
algo_return = (np.exp(strategy_log_returns.sum()) - 1) * 100

print("-" * 30)
print(f"Buy & Hold Return: {buy_and_hold_return:.2f}%")
print(f"Algorithm Return:  {algo_return:.2f}%")
print("-" * 30)