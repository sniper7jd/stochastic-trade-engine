import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 1. Load keys and initialize the client
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

trade_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

# 2. Build the order request
order_details = MarketOrderRequest(
    symbol="V",
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY
)

# 3. Submit the order to the paper exchange
print("Submitting market order for 1 share of AAPL...")
market_order = trade_client.submit_order(order_data=order_details)

# 4. Print the confirmation
print(f"Order submitted successfully!")
print(f"Symbol: {market_order.symbol}")
print(f"Quantity: {market_order.qty}")
print(f"Status: {market_order.status}")
print(f"Client Order ID: {market_order.client_order_id}")