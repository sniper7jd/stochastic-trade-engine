import numpy as np
import matplotlib.pyplot as plt
import math

# 1. Define the true complex function (e.g., continuous growth/pricing curve)
def true_function(x):
    return np.exp(x)

# 2. Define the Taylor approximations centered around a starting price 'a'
# For e^x, the derivative is always e^x. 
# If our anchor point 'a' is 0, then f(0) = 1, f'(0) = 1, f''(0) = 1, etc.
def taylor_1st_order(x, a=0):
    """Delta (Linear speed)"""
    return np.exp(a) + np.exp(a) * (x - a)

def taylor_2nd_order(x, a=0):
    """Gamma (Quadratic acceleration)"""
    return taylor_1st_order(x, a) + (np.exp(a) / math.factorial(2)) * (x - a)**2

def taylor_3rd_order(x, a=0):
    """Speed of Gamma (Cubic jerk)"""
    return taylor_2nd_order(x, a) + (np.exp(a) / math.factorial(3)) * (x - a)**3

# 3. Calculate the Convergence Error
def calculate_error(true_val, approx_val):
    """Calculates the absolute error between the true curve and the model"""
    return np.abs(true_val - approx_val)

# --- Execute and Visualize ---

# Generate simulated market moves (x-axis)
# Let's say 0 is our current price, and we model drops to -3 and spikes to +3
market_moves = np.linspace(-3, 3, 100)

# Calculate values
y_true = true_function(market_moves)
y_delta = taylor_1st_order(market_moves)
y_gamma = taylor_2nd_order(market_moves)

# Calculate errors
error_delta = calculate_error(y_true, y_delta)
error_gamma = calculate_error(y_true, y_gamma)

# Plotting the curves
plt.figure(figsize=(12, 5))

# Subplot 1: The Curves
plt.subplot(1, 2, 1)
plt.plot(market_moves, y_true, label="True Option Price", linewidth=2, color='blue')
plt.plot(market_moves, y_delta, label="Delta Model (1st Order)", linestyle='--', color='orange')
plt.plot(market_moves, y_gamma, label="Gamma Model (2nd Order)", linestyle='-.', color='green')
plt.title("Pricing Models (Convergence)")
plt.xlabel("Market Move away from Current Price")
plt.ylabel("Asset Value")
plt.ylim(-1, 10)
plt.legend()
plt.grid(True)

# Subplot 2: The Error (When the bot blows up)
plt.subplot(1, 2, 2)
plt.plot(market_moves, error_delta, label="Error: Delta Only", color='orange')
plt.plot(market_moves, error_gamma, label="Error: Delta + Gamma", color='green')
plt.title("Convergence Error (Risk)")
plt.xlabel("Market Move away from Current Price")
plt.ylabel("Pricing Error ($)")
plt.ylim(0, 10)
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()