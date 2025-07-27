import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from coinbase.advanced_trade.client import AsyncCoinbaseAdvancedTradeClient

# Load the Ed25519 API credentials from JSON
def load_api_credentials():
    with open("cdp_api_key.json") as f:
        data = json.load(f)
    return data

# Initialize client
def get_coinbase_client():
    creds = load_api_credentials()
    return AsyncCoinbaseAdvancedTradeClient(api_key=creds["apiKey"], api_secret=creds["apiSecret"])

# Fetch candles and return as a pandas DataFrame
async def get_candles(client, product_id="XLM-USD", granularity="ONE_MINUTE", start=None, end=None):
    candles = await client.get_product_candles(product_id, granularity=granularity)
    rows = [
        {
            "time": datetime.utcfromtimestamp(int(c.time)).strftime("%Y-%m-%d %H:%M:%S"),
            "low": float(c.low),
            "high": float(c.high),
            "open": float(c.open),
            "close": float(c.close),
            "volume": float(c.volume),
        }
        for c in candles.candles
    ]
    df = pd.DataFrame(rows)
    df = df.sort_values(by="time")  # Ascending order
    return df

async def main():
    client = get_coinbase_client()
    
    # Fetch and print recent candles
    df = await get_candles(client, product_id="XLM-USD", granularity="ONE_MINUTE")
    print(df.tail())

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
