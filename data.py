import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Load your keys
load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

# Initialize the historical data client
data_client = StockHistoricalDataClient(api_key, secret_key)

# Set the time window to the last 10 days
end_date = datetime.now()
start_date = end_date - timedelta(days=10)

# Create the request for daily bars for Apple (AAPL)
request_params = StockBarsRequest(
    symbol_or_symbols="V",
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)

# Fetch and print the data
bars = data_client.get_stock_bars(request_params)

# .df converts the raw data into a pandas DataFrame
print(bars.df)