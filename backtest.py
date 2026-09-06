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


close_prices = bars.xs(target_stock, level='symbol')['close']
volume = bars.xs(target_stock, level='symbol')['volume']

# 1. Base Strategy Logic (From Previous Days)
log_returns = np.log(close_prices / close_prices.shift(1)).fillna(0)
rolling_mean = log_returns.rolling(window=15).mean()
daily_vol = log_returns.rolling(window=15).std()
z_scores = (log_returns - rolling_mean) / daily_vol

# Generate 1 (Long) or 0 (Neutral) signals
positions = np.select([z_scores < -1.5, z_scores > 1.5], [1, 0], default=0)
positions_series = pd.Series(positions, index=close_prices.index)

# 2. Portfolio Sizing (The Missing Link)
STARTING_CAPITAL = 100000

# How many shares do we hold if we allocate 100% of capital?
# We shift the signal by 1 so we calculate shares based on the price when we actually trade
target_shares = (positions_series.shift(1) * STARTING_CAPITAL) / close_prices
target_shares = target_shares.fillna(0)

# .diff() calculates the exact number of shares bought or sold that day
trade_qty = np.abs(target_shares.diff().fillna(0))

# 3. Vectorized Market Impact (The Square-Root Law)
GAMMA = 0.1  # Empirical constant for institutional impact
adv = volume.rolling(window=20).mean().replace(0, np.nan) # 20-day Average Daily Volume

# The Formula: Impact = Gamma * Volatility * sqrt(Trade Size / ADV) * Price * Trade Size
slippage_cost = GAMMA * daily_vol * np.sqrt(trade_qty / adv) * close_prices * trade_qty
slippage_cost = slippage_cost.fillna(0)

# 4. Vectorized Fixed Commissions
# Standard tiered pricing is often ~$0.005 per share
commission_cost = trade_qty * 0.005

# 5. Net P&L Calculation
# Gross P&L is simply the number of shares held * the dollar change in price today
price_change = close_prices.diff().fillna(0)
gross_pnl = target_shares.shift(1).fillna(0) * price_change

# Subtract the friction!
net_pnl = gross_pnl - slippage_cost - commission_cost

# 6. Reconstruct the Equity Curve
cumulative_net_equity = STARTING_CAPITAL + net_pnl.cumsum()

print(f"Starting Capital: ${STARTING_CAPITAL:,.2f}")
print(f"Final Gross Equity: ${(STARTING_CAPITAL + gross_pnl.cumsum().iloc[-1]):,.2f}")
print(f"Final Net Equity:   ${cumulative_net_equity.iloc[-1]:,.2f}")
print(f"Total Lost to Friction: ${(slippage_cost.sum() + commission_cost.sum()):,.2f}")