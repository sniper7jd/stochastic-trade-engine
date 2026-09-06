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

target_stock = "SPY"
print(f"Fetching 3 years of historical data for {target_stock}...")

end_date = datetime.now()
start_date = end_date - timedelta(days=3*365)

request_params = StockBarsRequest(
    symbol_or_symbols=target_stock,
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)
bars = data_client.get_stock_bars(request_params).df
close_prices = bars.xs(target_stock, level='symbol')['close']
volume = bars.xs(target_stock, level='symbol')['volume']

# 1. Split the Data
# We use the most recent 365 days as our blind Out-of-Sample (OOS) test
split_date = close_prices.index[-252] # Approx 252 trading days in a year

# IN-SAMPLE: The first 2 years
is_close = close_prices.loc[:split_date]
is_returns = np.log(is_close / is_close.shift(1)).fillna(0)

# OUT-OF-SAMPLE: The last 1 year
oos_close = close_prices.loc[split_date:]
oos_volume = volume.loc[split_date:]
oos_returns = np.log(oos_close / oos_close.shift(1)).fillna(0)

print(f"In-Sample (Training) Days: {len(is_close)}")
print(f"Out-of-Sample (Testing) Days: {len(oos_close)}")
print("-" * 40)

# 2. Grid Search Optimization (On In-Sample Data Only)
windows = [5, 10, 15, 20, 30]
z_thresholds = [1.0, 1.25, 1.5, 1.75, 2.0]
results = []

print("Running Grid Search on In-Sample Data...")
for w in windows:
    rolling_mean = is_returns.rolling(window=w).mean()
    rolling_vol = is_returns.rolling(window=w).std()
    z_scores = (is_returns - rolling_mean) / rolling_vol
    
    for t in z_thresholds:
        positions = np.select([z_scores < -t, z_scores > t], [1, 0], default=0)
        positions_series = pd.Series(positions, index=is_close.index)
        strategy_returns = positions_series.shift(1) * is_returns
        
        # Calculate raw gross return for ranking
        algo_return = (np.exp(strategy_returns.sum()) - 1) * 100
        results.append({'Window': w, 'Z-Threshold': t, 'Return (%)': algo_return})

results_df = pd.DataFrame(results)
best_params = results_df.loc[results_df['Return (%)'].idxmax()]

best_w = int(best_params['Window'])
best_t = best_params['Z-Threshold']

print(f"BEST IN-SAMPLE PARAMS FOUND: Window = {best_w}, Z-Threshold = {best_t}")
print(f"In-Sample Gross Return: {best_params['Return (%)']:.2f}%")
print("-" * 40)

# 3. Out-Of-Sample Validation (The Reality Check)
print("Testing Best Params on Out-of-Sample Data (with Friction)...")

# Apply the best parameters to the unseen data
oos_rolling_mean = oos_returns.rolling(window=best_w).mean()
oos_rolling_vol = oos_returns.rolling(window=best_w).std()
oos_z_scores = (oos_returns - oos_rolling_mean) / oos_rolling_vol

oos_positions = np.select([oos_z_scores < -best_t, oos_z_scores > best_t], [1, 0], default=0)
oos_positions_series = pd.Series(oos_positions, index=oos_close.index)

# Friction & Portfolio Math on the OOS Data
STARTING_CAPITAL = 100000
target_shares = (oos_positions_series.shift(1) * STARTING_CAPITAL) / oos_close
target_shares = target_shares.fillna(0)
trade_qty = np.abs(target_shares.diff().fillna(0))

GAMMA = 0.1
adv = oos_volume.rolling(window=20).mean().replace(0, np.nan)
slippage_cost = GAMMA * oos_rolling_vol * np.sqrt(trade_qty / adv) * oos_close * trade_qty
slippage_cost = slippage_cost.fillna(0)
commission_cost = trade_qty * 0.005

gross_pnl = target_shares.shift(1).fillna(0) * oos_close.diff().fillna(0)
net_pnl = gross_pnl - slippage_cost - commission_cost

# 4. Final OOS Results
oos_buy_hold_gross = (np.exp(oos_returns.sum()) - 1) * 100
oos_algo_net_return = (net_pnl.sum() / STARTING_CAPITAL) * 100

print(f"OOS Buy & Hold Return:  {oos_buy_hold_gross:.2f}%")
print(f"OOS Algorithm Return:   {oos_algo_net_return:.2f}% (Net of Friction)")

if oos_algo_net_return > 0 and oos_algo_net_return > oos_buy_hold_gross:
    print("\nCONCLUSION: Strategy survived OOS validation and beat the market! Ready for paper deployment.")
elif oos_algo_net_return > 0:
    print("\nCONCLUSION: Strategy is profitable, but underperformed Buy & Hold. Further model refinement needed.")
else:
    print("\nCONCLUSION: Strategy failed OOS validation. It overfit the training data and collapsed in real conditions.")