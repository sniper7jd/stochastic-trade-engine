import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# 1. Authenticate to the Paper Environment
load_dotenv()
trade_client = TradingClient(api_key=os.environ.get("ALPACA_API_KEY"), 
                             secret_key=os.environ.get("ALPACA_SECRET_KEY"), 
                             paper=True)  # <-- This protects your real bank account

# 2. Check Account Balance & P&L
account = trade_client.get_account()
initial_balance = 100000.00
current_equity = float(account.equity)
total_pnl = current_equity - initial_balance

print(f"--- Algorithmic Trading Dashboard ---")
print(f"Total Equity: ${current_equity:,.2f}")
print(f"Total P&L:    ${total_pnl:,.2f} ({(total_pnl/initial_balance)*100:.2f}%)")
print(f"Buying Power: ${float(account.buying_power):,.2f}")
print("-" * 37)

# 3. Audit Open Options & Stock Positions
positions = trade_client.get_all_positions()

if not positions:
    print("No open positions. Portfolio is currently in cash.")
else:
    for p in positions:
        print(f"Asset: {p.symbol}")
        print(f"Asset Class: {p.asset_class}")
        print(f"Quantity:    {p.qty}")
        print(f"Entry Price: ${float(p.avg_entry_price):.2f}")
        print(f"Live Price:  ${float(p.current_price):.2f}")
        print(f"Live P&L:    ${float(p.unrealized_pl):.2f} ({float(p.unrealized_plpc)*100:.2f}%)")
        print("-" * 25)