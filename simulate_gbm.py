import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# 1. Fetch Data
load_dotenv()
data_client = StockHistoricalDataClient(os.environ.get("ALPACA_API_KEY"), 
                                        os.environ.get("ALPACA_SECRET_KEY"))

target_stock = "AAPL"
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

# 2. Calculate Drift and Volatility (Log Returns)
log_returns = np.log(close_prices / close_prices.shift(1)).dropna()

u = log_returns.mean()
var = log_returns.var()

# Drift calculation mathematically adjusted for volatility drag (Itô's lemma application)
drift = u - (0.5 * var)
stdev = log_returns.std()

# 3. Monte Carlo Setup
days_to_simulate = 30
iterations = 1000  # We will simulate 1,000 different alternate realities
current_price = close_prices.iloc[-1]

# 4. Generate Random Brownian Motion Shocks
# np.random.rand generates the random standard normal variables
Z = np.random.normal(size=(days_to_simulate, iterations))

# 5. Calculate Daily Growth Multipliers using the GBM Formula
# daily_step = exp(drift + stdev * Z)
daily_step = np.exp(drift + stdev * Z)

# 6. Vectorized Price Path Generation (No loops needed!)
# np.cumprod compounds the returns day over day across all 1,000 simulations
price_paths = current_price * np.cumprod(daily_step, axis=0)

# 7. Distribution Analysis
# Extract the 1,000 prices at Day 30 (the last row of the simulation)
terminal_prices = price_paths[-1]

# 8. Options Pricing (Monte Carlo Method)
# Define the contract parameters
strike_price = 382.00
risk_free_rate = 0.045 # Assume a 4.5% risk-free rate based on current US Treasuries
time_in_years = days_to_simulate / 252.0 # Trading days in a year

# Calculate the payoff for a Call option in all 1,000 alternate realities
# A call option is worth (Price - Strike), or $0 if it expires out-of-the-money
call_payoffs = np.maximum(terminal_prices - strike_price, 0)

# The Expected Future Value is just the average payoff across all simulations
expected_future_value = np.mean(call_payoffs)

# Discount it back to Present Value using continuous compounding: PV = FV * e^(-rT)
fair_value_call = expected_future_value * np.exp(-risk_free_rate * time_in_years)

print("-" * 40)
print(f"Options Pricing Engine (Monte Carlo)")
print("-" * 40)
print(f"Strike Price:          ${strike_price:.2f}")
print(f"Risk-Free Rate:        {risk_free_rate * 100}%")
print(f"Simulated Fair Value:  ${fair_value_call:.2f}")