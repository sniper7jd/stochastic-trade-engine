import os
import math
from datetime import datetime
from dotenv import load_dotenv

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockLatestQuoteRequest

# 1. Setup & Authentication
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

if not api_key or not secret_key:
    raise ValueError("Alpaca API credentials not found in environment variables.")

options_client = OptionHistoricalDataClient(api_key, secret_key)
stock_client = StockHistoricalDataClient(api_key, secret_key)

RISK_FREE_RATE = 0.0475  # 4.75% Treasury yield benchmark
ASSUMED_IV = 0.25       # 25% annualized baseline volatility

# 2. Black-Scholes Pricing & Greeks Engine
def norm_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

def calculate_d1_d2(S, K, T, r, sigma):
    if T <= 0.0001:
        return 0.0, 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2

def black_scholes_call(S, K, T, r, sigma):
    """Calculates theoretical call option price."""
    if T <= 0.0001:
        return max(0.0, S - K)
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    return (S * norm_cdf(d1)) - (K * math.exp(-r * T) * norm_cdf(d2))

def call_daily_theta(S, K, T, r, sigma):
    """
    Calculates 1-day Black-Scholes Theta decay in dollars/share.
    Negative value represents daily value loss attributable purely to time passing.
    """
    if T <= 0.001:
        return 0.0
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    # Annualized Theta formula
    term1 = -(S * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(T))
    term2 = -r * K * math.exp(-r * T) * norm_cdf(d2)
    annual_theta = term1 + term2
    return annual_theta / 365.0  # Converted to 1-calendar-day dollar decay

# 3. User Input Prompts
print("=" * 70)
print("       TARGET-DRIVEN OTM CALL SCANNER & THETA ANALYZER        ")
print("=" * 70)

ticker = input("Enter ticker symbol (e.g., AAPL): ").strip().upper()
target_price = float(input(f"Enter your expected target price for {ticker} ($): "))
timeframe_days = int(input("Enter expected timeframe to hit target (in days): "))

today = datetime.now()

# 4. Fetch Live Spot Price
print(f"\n[1/3] Fetching live market quote for {ticker}...")
stock_req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
quote = stock_client.get_stock_latest_quote(stock_req)
current_spot = quote[ticker].ask_price
print(f"Current Spot Price: ${current_spot:.2f} | Target: ${target_price:.2f} ({((target_price/current_spot)-1)*100:+.2f}%)")

# 5. Fetch Full Option Chain
print(f"[2/3] Fetching active options chain for {ticker}...")
chain_req = OptionChainRequest(underlying_symbol=ticker)
chain = options_client.get_option_chain(chain_req)

# Find all unique expiration dates in the chain
unique_expirations = set()
for contract_symbol in chain.keys():
    date_str = contract_symbol[-15:-9]
    unique_expirations.add(date_str)

if not unique_expirations:
    raise ValueError(f"No option chain contracts returned for {ticker}.")

# 6. Map to the Nearest Expiration Date
exp_dates = []
for d_str in unique_expirations:
    exp_dt = datetime.strptime(d_str, "%y%m%d")
    dte = (exp_dt - today).days
    if dte > 0:
        exp_dates.append((abs(dte - timeframe_days), dte, exp_dt, d_str))

exp_dates.sort(key=lambda x: x[0])
best_diff, matched_dte, matched_exp_date, matched_date_str = exp_dates[0]

print(f"[3/3] Target timeframe: {timeframe_days} days.")
print(f"Nearest Available Expiration: {matched_exp_date.strftime('%Y-%m-%d')} ({matched_dte} DTE)")
print(f"Time Buffer / Runway remaining after move: {matched_dte - timeframe_days} days\n")

# 7. Scan and Analyze Out-of-the-Money Calls
otm_calls = []

for contract_symbol, snapshot in chain.items():
    if not snapshot.latest_quote:
        continue

    # Match selected expiration and call type ('C')
    if contract_symbol[-15:-9] != matched_date_str or contract_symbol[-9] != 'C':
        continue

    strike = float(contract_symbol[-8:]) / 1000.0

    # Strict OTM filter: strike must be above current spot
    if strike <= current_spot:
        continue

    ask = snapshot.latest_quote.ask_price
    bid = snapshot.latest_quote.bid_price
    mid = (ask + bid) / 2.0 if (bid > 0 and ask > 0) else ask

    if ask <= 0.0:
        continue

    # Time parameters in years
    t_now = matched_dte / 365.0
    remaining_days = max(0, matched_dte - timeframe_days)
    t_at_target = remaining_days / 365.0

    # Calculate Current Daily Theta
    current_theta = call_daily_theta(current_spot, strike, t_now, RISK_FREE_RATE, ASSUMED_IV)

    # Calculate Projected Value when underlying hits target_price at target timeframe
    projected_val = black_scholes_call(target_price, strike, t_at_target, RISK_FREE_RATE, ASSUMED_IV)

    # Intrinsic value at expiration if underlying hits target_price
    intrinsic_at_target = max(0.0, target_price - strike)

    expected_roi = ((projected_val - ask) / ask) * 100.0 if ask > 0 else 0.0

    otm_calls.append({
        "contract": contract_symbol,
        "strike": strike,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "theta": current_theta,
        "projected_val": projected_val,
        "intrinsic": intrinsic_at_target,
        "roi": expected_roi
    })

# 8. Sort by Strike and Display Results
otm_calls.sort(key=lambda x: x["strike"])

print("=" * 95)
print(f"{'STRIKE':<8} {'BID/ASK':<14} {'DAILY THETA':<13} {'PROJ VAL':<11} {'INTRINSIC':<11} {'EXP ROI':<10} {'CONTRACT'}")
print("=" * 95)

for c in otm_calls:
    bid_ask_str = f"${c['bid']:.2f}/${c['ask']:.2f}"
    theta_str = f"${c['theta']:.3f}/day"
    print(f"${c['strike']:<7.2f} {bid_ask_str:<14} {theta_str:<13} ${c['projected_val']:<10.2f} "
          f"${c['intrinsic']:<10.2f} {c['roi']:>+7.1f}%  {c['contract']}")

print("=" * 95)
print("Key Metrics:")
print(" • DAILY THETA: Dollar loss per share per calendar day while waiting for the move.")
print(" • PROJ VAL: Estimated option resale price on target day if underlying hits target.")
print(f" • RUNWAY: {matched_dte - timeframe_days} days left after target date before expiration wipes out remaining extrinsic value.")
print("=" * 95)