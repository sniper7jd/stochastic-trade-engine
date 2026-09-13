import os
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream

load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")
stream = StockDataStream(api_key, secret_key)

# 1. The VWAP Memory Bank (State Management)
# This lives outside the handler so it doesn't reset when a new trade arrives
market_state = {
    "cumulative_notional": 0.0,
    "cumulative_volume": 0
}

# 2. The Upgraded Event Handler
async def trade_handler(data):
    symbol = data.symbol
    price = data.price
    size = data.size
    timestamp = data.timestamp.strftime('%H:%M:%S.%f')[:-3]
    
    # Calculate the dollar value of this specific trade
    trade_notional = price * size
    
    # Update our global memory bank
    market_state["cumulative_notional"] += trade_notional
    market_state["cumulative_volume"] += size
    
    # Calculate the live VWAP instantly
    live_vwap = market_state["cumulative_notional"] / market_state["cumulative_volume"]
    
    # Print the execution and the VWAP tracker
    print(f"[{timestamp}] {symbol} | Trade: {size:4} @ ${price:.2f} | Live VWAP: ${live_vwap:.2f}")

target_symbol = "SPY"
print(f"Opening WebSocket for {target_symbol} to calculate live VWAP...")
print("Waiting for the market data...\n")

stream.subscribe_trades(trade_handler, target_symbol)

try:
    stream.run()
except KeyboardInterrupt:
    print("\nWebSocket connection closed by user.")