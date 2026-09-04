import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# Load environment variables from the .env file
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

# Initialize the client. paper=True routes to the simulated market.
trade_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

# Fetch and print account details
account = trade_client.get_account()
print(f"Paper Account Status: {account.status}")
print(f"Available Buying Power: ${account.buying_power}")