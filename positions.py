import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()
trade_client = TradingClient(api_key=os.environ.get("ALPACA_API_KEY"), 
                             secret_key=os.environ.get("ALPACA_SECRET_KEY"), 
                             paper=True)

# Fetch all open positions
portfolio = trade_client.get_all_positions()

if not portfolio:
    print("Your portfolio is currently empty.")
else:
    print("--- Open Positions ---")
    for position in portfolio:
        print(f"Symbol: {position.symbol}")
        print(f"Quantity: {position.qty}")
        print(f"Average Entry Price: ${position.avg_entry_price}")
        print(f"Current Market Price: ${position.current_price}")
        print(f"Unrealized P&L: ${position.unrealized_pl}")
        print("-" * 20)