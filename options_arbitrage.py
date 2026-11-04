import os
from dotenv import load_dotenv

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest

# 1. Setup
load_dotenv()
options_client = OptionHistoricalDataClient(os.environ.get("ALPACA_API_KEY"), 
                                            os.environ.get("ALPACA_SECRET_KEY"))

underlying_symbol = "AAPL"
theoretical_ceiling = 382.32  # Use the exact 95% ceiling from the Monte Carlo
fair_value_model = 0.62  

print(f"Fetching Live Options Chain for {underlying_symbol}...")

req = OptionChainRequest(underlying_symbol=underlying_symbol)
chain = options_client.get_option_chain(req)

print("-" * 40)
print(f"Finding the closest available Call Option to ${theoretical_ceiling:.2f}")
print("-" * 40)

available_calls = []

# 2. Scan and Parse the Entire Chain
for contract_symbol, snapshot in chain.items():
    # A standard OCC symbol looks like: AAPL261016C00382000
    # The last 15 characters always contain the Date, Type (C/P), and Strike
    right_side = contract_symbol[-15:] 
    is_call = right_side[6] == 'C'
    strike = int(right_side[7:]) / 1000.0
    
    if is_call:
        # Calculate how far this strike is from our theoretical ceiling
        distance = abs(strike - theoretical_ceiling)
        available_calls.append((distance, strike, contract_symbol, snapshot))

# 3. Sort and Select the Best Match
if not available_calls:
    print("No call options found for this asset.")
else:
    # Sort the list by the 'distance' (the first element in our tuple)
    available_calls.sort(key=lambda x: x[0])
    
    # Grab the absolute closest match
    best_match = available_calls[0]
    closest_strike = best_match[1]
    contract = best_match[2]
    snapshot = best_match[3]

    # Calculate real market price from the bid/ask spread
    bid = snapshot.latest_quote.bid_price if snapshot.latest_quote else 0
    ask = snapshot.latest_quote.ask_price if snapshot.latest_quote else 0
    mid_price = (bid + ask) / 2 if (bid > 0 and ask > 0) else 0

    print(f"Closest Available Strike: ${closest_strike:.2f}")
    print(f"Contract:     {contract}")
    print(f"Market Bid:   ${bid:.2f}")
    print(f"Market Ask:   ${ask:.2f}")
    print(f"Market Mid:   ${mid_price:.2f}")
    print("-" * 20)
    
    if mid_price > 0:
        print("Market data successfully retrieved. Ready for arbitrage logic.")
    else:
        print("Warning: Bid/Ask is $0.00. This specific contract is currently illiquid.")