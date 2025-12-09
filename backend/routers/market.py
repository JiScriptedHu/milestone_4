from fastapi import APIRouter, HTTPException
import yfinance as yf
import pandas as pd
import asyncio
import logging

router = APIRouter()

# -----------------------------
# Logging Configuration
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Helper Function
# -----------------------------
def fetch_5y_data_sync(ticker: str):
    """
    Fetches 5-year OHLC historical data along with metadata.
    Returns a structured dictionary or None if no data is available.
    """
    stock = yf.Ticker(ticker)

    # 1. Fetch 5-year historical data
    hist = stock.history(period="5y", auto_adjust=True)
    if hist.empty:
        return None

    # 2. Default metadata
    full_name = ticker.upper()
    currency = "USD"
    exchange = "MARKET"

    try:
        # A. Fetch stock metadata
        stock_meta = stock.info
        full_name = stock_meta.get('longName') or stock_meta.get('shortName') or full_name

        # B. Fetch currency & exchange safely
        fast_info = stock.fast_info
        currency = fast_info.get('currency', currency)
        raw_exchange = fast_info.get('exchange', 'UNKNOWN')
        exchange_map = {
            "NSI": "NSE", "NMS": "NASDAQ", "NYQ": "NYSE",
            "PNK": "OTC", "LSE": "LSE", "BSE": "BSE",
            "GER": "XETRA", "PAR": "EURONEXT"
        }
        exchange = exchange_map.get(raw_exchange, raw_exchange)

    except Exception as e:
        logger.warning(f"Failed to fetch metadata for {ticker}: {e}")

    # 3. Clean and format historical data
    hist.reset_index(inplace=True)
    hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
    hist = hist.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })
    final_df = hist[['date', 'open', 'high', 'low', 'close', 'volume']]

    # 4. Return structured response
    return {
        "ticker": ticker.upper(),
        "name": full_name,
        "exchange": exchange,
        "currency": currency,
        "data": final_df.to_dict(orient="records")
    }

# -----------------------------
# API Endpoint
# -----------------------------
@router.get("/{ticker}")
async def get_ohlc_5y(ticker: str):
    """
    Async endpoint to get 5-year OHLC data for a given ticker.
    """
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, fetch_5y_data_sync, ticker)
        if data is None:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))