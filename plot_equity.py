import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# 1. Setup & Data Fetching
load_dotenv()
data_client = StockHistoricalDataClient(os.environ.get("ALPACA_API_KEY"), 
                                        os.environ.get("ALPACA_SECRET_KEY"))

target_stock = "SPY"
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

# 2. Mathematical Models (Using a 15-day window and 1.5 Z-score threshold)
log_returns = np.log(close_prices / close_prices.shift(1)).fillna(0)

rolling_mean = log_returns.rolling(window=15).mean()
rolling_vol = log_returns.rolling(window=15).std()
z_scores = (log_returns - rolling_mean) / rolling_vol

conditions = [z_scores < -1.5, z_scores > 1.5]
choices = [1, -1]
positions = np.select(conditions, choices, default=0)
positions_series = pd.Series(positions, index=close_prices.index)

strategy_log_returns = positions_series.shift(1) * log_returns
strategy_log_returns = strategy_log_returns.fillna(0)

# 3. Calculate Cumulative Returns
# We use cumsum() to add up the log returns day by day, 
# then np.exp() to convert them back into a regular multiplier (1.0 = starting capital)
cumulative_buy_hold = np.exp(log_returns.cumsum())
cumulative_algo = np.exp(strategy_log_returns.cumsum())

# 4. Data Visualization with Matplotlib
plt.figure(figsize=(12, 6))

# Plot the baseline and the algorithm
plt.plot(cumulative_buy_hold, label='Buy & Hold (SPY)', color='blue', alpha=0.5)
plt.plot(cumulative_algo, label='Z-Score Algorithm', color='orange', linewidth=2)

# Formatting
plt.title(f'Equity Curve: Statistical Mean Reversion vs Buy & Hold ({target_stock})')
plt.xlabel('Date')
plt.ylabel('Cumulative Return (1.0 = Initial Capital)')
plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.6)

# Display the plot in a new window
plt.tight_layout()
plt.show()