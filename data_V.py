import numpy as np

np.random.seed(42)
n_simulations = 10000

# Base financial assumptions for Visa (in Millions USD)
fcf_t1 = 21500  # Base Year 1 Free Cash Flow projection
shares_out = 1870  # Visa's actual diluted share count is ~1.87B
current_price = 375.0

# Distributions for key variables
# WACC: Normal distribution centered at 7.8% 
wacc = np.random.normal(0.078, 0.003, n_simulations)
# Terminal Growth: Normal distribution centered at 3.3%
g_terminal = np.random.normal(0.033, 0.0025, n_simulations)
# 5-year CAGR of FCF: Center at 14.5% (driven by high-margin Value-Added Services)
fcf_growth = np.random.normal(0.145, 0.010, n_simulations)

# Simple 5-year DCF simulation
intrinsic_values = []
for i in range(n_simulations):
    r = wacc[i]
    g = g_terminal[i]
    growth = fcf_growth[i]

    if r <= g:
        continue

    # Discounted cash flows for years 1-5
    pv_cf = sum([fcf_t1 * ((1 + growth) ** t) / ((1 + r) ** t) for t in range(1, 6)])
    
    # Terminal value at Year 5
    fcf_5 = fcf_t1 * ((1 + growth) ** 5)
    tv = (fcf_5 * (1 + g)) / (r - g)
    pv_tv = tv / ((1 + r) ** 5)

    ev = pv_cf + pv_tv
    equity_val = ev  # Net debt impact is negligible relative to market cap
    intrinsic_values.append(equity_val / shares_out)

intrinsic_values = np.array(intrinsic_values)
median_val = np.median(intrinsic_values)
prob_undervalued = np.mean(intrinsic_values > current_price) * 100

print(f"Median Target Price: ${median_val:.2f}")
print(f"Probability Fair Value > ${current_price}: {prob_undervalued:.1f}%")
print(f"25th Percentile (Downside): ${np.percentile(intrinsic_values, 25):.2f}")
print(f"75th Percentile (Upside): ${np.percentile(intrinsic_values, 75):.2f}")