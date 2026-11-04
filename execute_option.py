import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 1. Authenticate the Trading Client
load_dotenv()
trade_client = TradingClient(api_key=os.environ.get("ALPACA_API_KEY"), 
                             secret_key=os.environ.get("ALPACA_SECRET_KEY"), 
                             paper=True)

# 2. Define the exact OCC contract and our calculated price
contract_symbol = "AAPL260918C00380000"
mid_price = 0.05  # We refuse to pay the $0.09 ask price

# 3. Build the Limit Order
print(f"Constructing Limit Order for {contract_symbol} at ${mid_price:.2f}...")

option_order = LimitOrderRequest(
    symbol=contract_symbol,
    qty=1, # 1 contract controls 100 shares of Apple
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
    limit_price=mid_price 
)

# 4. Submit the Order
try:
    submitted_order = trade_client.submit_order(order_data=option_order)
    print("\n--- ORDER SUBMITTED SUCCESSFULLY ---")
    print(f"Order ID:      {submitted_order.id}")
    print(f"Status:        {submitted_order.status}")
    print(f"Asset Class:   {submitted_order.asset_class}")
    print(f"Limit Price:   ${submitted_order.limit_price}")
    
    # 5. Check if it filled instantly or is resting on the order book
    if submitted_order.status == 'filled':
        print("Result: Order filled immediately at the mid-price!")
    else:
        print("Result: Order is resting on the exchange waiting for a seller.")
        
except Exception as e:
    print(f"\nOrder Failed: {e}")