import os
from datetime import datetime
from dotenv import load_dotenv
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockLatestQuoteRequest

# 1. Setup & Authentication
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

options_client = OptionHistoricalDataClient(api_key, secret_key)
stock_client = StockHistoricalDataClient(api_key, secret_key)

target_symbols = ["AAPL", "JNJ", "XOM", "JPM", "WMT"]
today = datetime.now()
best_contracts_per_symbol = {}

print("--- Initializing Smart Black Swan Scanner ---")

for symbol in target_symbols:
    try:
        # 2. Fetch Live Stock Price for Context
        stock_req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        latest_quote = stock_client.get_stock_latest_quote(stock_req)
        current_price = latest_quote[symbol].ask_price
        
        print(f"Scanning {symbol} (Live Price: ${current_price:.2f})...")
        
        req = OptionChainRequest(underlying_symbol=symbol)
        chain = options_client.get_option_chain(req)
        valid_contracts = []
        
        for contract_symbol, snapshot in chain.items():
            if snapshot.latest_quote:
                ask_price = snapshot.latest_quote.ask_price
                
                # EXTRACT DATE (Characters -15 to -9)
                date_str = contract_symbol[-15:-9]
                expiration_date = datetime.strptime(date_str, "%y%m%d")
                dte = (expiration_date - today).days
                
                # EXTRACT TYPE (Character -9)
                option_type = contract_symbol[-9]
                
                # EXTRACT STRIKE PRICE (Last 8 characters, divided by 1000)
                strike_str = contract_symbol[-8:]
                strike_price = float(strike_str) / 1000
                
                # 3. The Reality Filter (No Bankruptcy Strikes)
                # Puts must be 20% to 50% below current price.
                # Calls must be 20% to 50% above current price.
                is_valid_put = option_type == 'P' and (current_price * 0.50 <= strike_price <= current_price * 0.80)
                is_valid_call = option_type == 'C' and (current_price * 1.20 <= strike_price <= current_price * 1.50)
                
                # The Triple Filter: 30-90 DTE + Cheap ($0.05 max) + Realistic Strike
                if 30 <= dte <= 90 and 0.00 < ask_price <= 0.05 and (is_valid_put or is_valid_call):
                    valid_contracts.append({
                        "contract": contract_symbol,
                        "ask_price": ask_price,
                        "dte": dte,
                        "type": option_type,
                        "strike": strike_price,
                        "distance": abs(current_price - strike_price) # Used for sorting
                    })
        
        if valid_contracts:
            # Sort by price first, then by closest strike distance
            valid_contracts.sort(key=lambda x: (x["ask_price"], x["distance"]))
            best_contracts_per_symbol[symbol] = valid_contracts[0]
            
    except Exception as e:
        print(f"Could not fetch data for {symbol}: {e}")

# 4. Display the Output
print("\n" + "="*75)
print(f"{'TICKER':<7} {'DTE':<5} {'TYPE':<5} {'STRIKE':<9} {'ASK':<7} {'CONTRACT'}")
print("="*75)

total_cost = 0
for symbol, data in best_contracts_per_symbol.items():
    total_cost += data['ask_price']
    print(f"{symbol:<7} {data['dte']:<5} {data['type']:<5} ${data['strike']:<8.2f} ${data['ask_price']:<6.2f} {data['contract']}")

print("-" * 75)
# Options are in lots of 100, so $0.01 actually costs $1.00
print(f"Total Portfolio Capital Required: ${(total_cost * 100):.2f}")
print("="*75)