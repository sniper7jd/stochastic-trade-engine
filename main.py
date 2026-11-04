import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta

# Alpaca imports
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 1. Setup & Authentication
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

data_client = StockHistoricalDataClient(api_key, secret_key)
trade_client = TradingClient(api_key, secret_key, paper=True)

SYMBOL = "META"
QTY = 1

print(f"--- Starting Trading Engine for {SYMBOL} ---")

# 2. Fetch Historical Data
end_date = datetime.now()
start_date = end_date - timedelta(days=20)

request_params = StockBarsRequest(
    symbol_or_symbols=SYMBOL,
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)
bars = data_client.get_stock_bars(request_params).df
close_prices = bars.xs(SYMBOL, level='symbol')['close']

# 3. Quantitative Signal Calculation (Z-Score)
rolling_mean = close_prices.rolling(window=5).mean()
rolling_std = close_prices.rolling(window=5).std()
z_scores = (close_prices - rolling_mean) / rolling_std

current_price = close_prices.iloc[-1]
current_z = z_scores.iloc[-1]

print(f"Latest Price: ${current_price:.2f} | Z-Score: {current_z:.2f}")

# 4. Check Current Portfolio State
try:
    position = trade_client.get_open_position(SYMBOL)
    currently_owned = int(position.qty)
    print(f"Current Position: {currently_owned} shares.")
except Exception:
    # Alpaca throws an error if the position doesn't exist, meaning we own 0.
    currently_owned = 0
    print("Current Position: 0 shares.")

# 5. Execution Logic with Risk Management
if current_z < -1.5:
    print("Signal: OVERSOLD.")
    if currently_owned == 0:
        print("Action: Executing BUY order.")
        order = MarketOrderRequest(symbol=SYMBOL, qty=QTY, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
        trade_client.submit_order(order_data=order)
    else:
        print("Action: HOLD. We already own this asset. Avoid over-exposure.")

elif current_z > 1.5:
    print("Signal: OVERBOUGHT.")
    if currently_owned > 0:
        print("Action: Executing SELL order to take profit.")
        order = MarketOrderRequest(symbol=SYMBOL, qty=currently_owned, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
        trade_client.submit_order(order_data=order)
    else:
        print("Action: HOLD. No inventory to sell.")

else:
    print("Signal: NEUTRAL. No action required.")

print("--- Engine Cycle Complete ---")