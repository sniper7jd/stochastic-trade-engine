import os
from dotenv import load_dotenv
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import numpy as np


load_dotenv()
data_client = StockHistoricalDataClient(os.environ.get("ALPACA_API_KEY"), 
                                        os.environ.get("ALPACA_SECRET_KEY"))

# 1. Fetch the last 20 days of data for Apple
end_date = datetime.now()
start_date = end_date - timedelta(days=20)

request_params = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)
bars = data_client.get_stock_bars(request_params).df

# The dataframe uses a multi-index (symbol, timestamp). 
# We extract just the 'close' prices for AAPL.

close_prices = bars.xs('AAPL', level='symbol')['close']

# 1. Calculate Log Returns (Continuous Compounding)
# We shift the prices by 1 day to compare today's close to yesterday's close
log_returns = np.log(close_prices / close_prices.shift(1))

# 2. Calculate Rolling Historical Volatility
# We use a 20-day window (roughly one trading month) to find the standard deviation of the returns
window = 20
rolling_volatility = log_returns.rolling(window=window).std()

# 3. Calculate the Moving Average of Log Returns
rolling_mean_return = log_returns.rolling(window=window).mean()

# 4. The Advanced Z-Score
# We isolate the most recent data point (today's return and today's volatility)
current_return = log_returns.iloc[-1]
current_volatility = rolling_volatility.iloc[-1]
current_mean_return = rolling_mean_return.iloc[-1]

# How many standard deviations did today's return deviate from the historical norm?
return_z_score = (current_return - current_mean_return) / current_volatility

print(f"Today's Log Return: {current_return:.4f}")
print(f"Current 20-Day Volatility: {current_volatility:.4f}")
print(f"Return Z-Score: {return_z_score:.2f}")

# 5. Volatility-Adjusted Execution Logic
if return_z_score < -2.0:
    print("Signal: STATISTICALLY OVERSOLD. A 2-sigma downside event occurred.")
    # Proceed to buy logic...
elif return_z_score > 2.0:
    print("Signal: STATISTICALLY OVERBOUGHT. A 2-sigma upside event occurred.")
    # Proceed to sell logic...
else:
    print("Signal: NEUTRAL (Within Normal Brownian Motion).")