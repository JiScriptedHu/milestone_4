from fastapi import APIRouter
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re
import traceback

# Import Linear Regression Model
try:
    from models.linear_regression_model import predict_linear_regression
except ImportError:
    predict_linear_regression = None

router = APIRouter()

# -----------------------------
# Pydantic Models
# -----------------------------
class ChatRequest(BaseModel):
    message: str

# -----------------------------
# Helper Functions
# -----------------------------
def get_market_data(ticker: str, period: str = "5y", start: str = None, end: str = None) -> pd.DataFrame:
    """
    Fetch historical market data.
    - If start/end are provided, fetches specific range (optimized).
    - Otherwise, uses 'period' (default 5y).
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Optimize fetch: Use start/end if provided, else use period
        if start and end:
            hist = stock.history(start=start, end=end)
        else:
            hist = stock.history(period=period)
            
        hist.index = pd.to_datetime(hist.index).date  # Normalize index to date only
        return hist
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def analyze_trend(hist: pd.DataFrame) -> str:
    """Analyze Bull/Bear trend using 50-day SMA."""
    if len(hist) < 50:
        return "Insufficient data for trend analysis"
    
    current_price = hist['Close'].iloc[-1]
    sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
    trend = "BULLISH (Bull)" if current_price > sma_50 else "BEARISH (Bear)"
    return f"{trend} (Price: {current_price:.2f} vs 50-day SMA: {sma_50:.2f})"

def parse_flexible_date(date_str: str):
    """Parse various date formats into datetime.date."""
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y",
        "%Y/%m/%d", "%y-%m-%d", "%d-%m-%y",
        "%d/%m/%y", "%y/%m/%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

# -----------------------------
# Chat Endpoint
# -----------------------------
@router.post("/")
async def chat_response(request: ChatRequest):
    user_msg = request.message.lower().strip()

    # Define suggestion messages
    forecast_msg = (
        "<br><br><i>For better comparison and advanced insights, "
        "check out the <a href='forecast.html' style='color:#007bff; text-decoration:none; font-weight:bold;'>Forecast</a>.</i>"
    )
    
    dashboard_msg = (
        "<br><br><i>For a better view of historical details, "
        "check out the <a href='index.html' style='color:#007bff; text-decoration:none; font-weight:bold;'>Market</a>.</i>"
    )

    # --- 1. Help / Guide ---
    if user_msg in ['help', 'guide', 'commands', 'usage']:
        guide_text = """
        <b>Available Commands:</b><br><br>
        1. <b>Latest Prices:</b> "Price of INFY.NS", "OHLC for AAPL"<br>
        2. <b>Historical Data:</b> "Close of TCS.NS on 25-10-2023"<br>
        3. <b>Trend Analysis:</b> "Is Wipro Bullish?", "Trend for RELIANCE.NS"<br>
        4. <b>Prediction:</b> "Predict INFY.NS for 26/12/2025"<br>
        5. <b>52-Week Range:</b> "52 week high of GOOGL"<br>
        """
        return {"response": guide_text}

    # --- 2. Extract Ticker ---
    ignore_list = {
        'OHLC', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'PRICE', 'TREND',
        'BULL', 'BEAR', 'HELP', 'GUIDE', 'COMMANDS', 'USAGE',
        'WEEK', 'YEAR', 'OF', 'IS', 'FOR', 'AND', 'VS', 'OR', 'ON', 'AT', 'DATE',
        'PREDICT', 'FORECAST', 'PREDICTION'
    }

    candidates = re.findall(r'\b[A-Z]{2,}(?:\.[A-Z]+)?\b', request.message)
    ticker = next((c for c in candidates if c not in ignore_list), None)

    # Fallback for common stocks
    if not ticker:
        for w in user_msg.split():
            if w.endswith('.ns') or w in ['infy', 'tcs', 'wipro', 'aapl', 'googl', 'tsla', 'reliance']:
                ticker = w.upper()
                if not ticker.endswith('.NS') and w in ['infy', 'tcs', 'wipro', 'reliance']:
                    ticker += ".NS"
                break

    if not ticker:
        return {"response": "I didn't catch a stock ticker. Specify one (e.g., 'Price of INFY.NS'). Type 'help' for examples."}

    # --- 3. Parse Date EARLY ---
    date_match = re.search(
        r'\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
        user_msg
    )
    parsed_date = parse_flexible_date(date_match.group(0)) if date_match else None

    # --- 4. Determine Data Fetch Strategy ---
    # Check if the user needs history (Trend, Prediction, 52-week High/Low)
    needs_history = any(k in user_msg for k in [
        'predict', 'forecast', 'trend', 'bull', 'bear', 'analysis', 
        '52 week', 'year high', 'year low'
    ])

    fetch_period = "5y"
    fetch_start = None
    fetch_end = None

    # OPTIMIZATION: If user asks for a specific date and DOES NOT need history/trends,
    # fetch ONLY that specific date.
    if parsed_date and not needs_history:
        fetch_start = parsed_date.strftime('%Y-%m-%d')
        fetch_end = (parsed_date + timedelta(days=1)).strftime('%Y-%m-%d')
        fetch_period = None  # Override period

    # --- 5. Fetch Data ---
    hist = get_market_data(ticker, period=fetch_period, start=fetch_start, end=fetch_end)

    if hist.empty:
        # If specific date fetch returned empty, it might be a holiday/weekend
        if fetch_start:
            return {"response": f"No trading data found for <b>{ticker}</b> on {fetch_start}. The market may have been closed."}
        return {"response": f"Could not retrieve data for {ticker}. Check the symbol and try again."}

    latest_date = hist.index[-1]
    latest = hist.iloc[-1]

    # --- 6. Prediction Intent (Linear Regression) ---
    if 'predict' in user_msg or 'forecast' in user_msg:
        if not predict_linear_regression:
            return {"response": "Prediction model is currently unavailable."}

        if not parsed_date:
            return {"response": "Please specify a future date for prediction. Example: 'Predict INFY.NS 26/12/2025'."}

        if parsed_date <= latest_date:
            return {"response": f"The date {parsed_date} is in the past. Use 'Price of {ticker} on {parsed_date}' for historical data."}

        days_diff = (parsed_date - latest_date).days

        if days_diff > 365:
            return {"response": "I can only predict up to 1 year in advance. Please choose a closer date."}

        # Prepare DataFrame for Model
        try:
            df_model = hist.copy().reset_index()
            df_model.rename(columns={df_model.columns[0]: 'date'}, inplace=True)
            df_model.rename(columns=lambda x: x.lower(), inplace=True)

            result = predict_linear_regression(df_model, days_forecast=days_diff, ticker=ticker)
            
            if not result or not result.get('forecast'):
                return {"response": "Prediction failed to generate results."}

            predicted_price = result['forecast'][-1]
            
            return {
                "response": (
                    f"<b>Prediction for {ticker}:</b><br>"
                    f"• Target Date: {parsed_date.strftime('%Y-%m-%d')}<br>"
                    f"• Model: Linear Regression<br>"
                    f"• Forecasted Price: <b>{predicted_price:.2f}</b>"
                    f"{forecast_msg}"
                )
            }
        except Exception as e:
            traceback.print_exc()
            return {"response": "An error occurred while running the prediction model."}

    # --- 7. Historical / Current Data Intents ---
    target_date = None
    target_row = latest

    # If we optimized the fetch, hist only has the target date.
    # If we didn't optimize (e.g. Trend query + Date), we need to find the date in history.
    if parsed_date:
        if parsed_date in hist.index:
            target_row = hist.loc[parsed_date]
            target_date = parsed_date
        elif not needs_history:
             # Should be caught by hist.empty above, but double check
             return {"response": f"No data found for {parsed_date}."}
        else:
             return {"response": f"No historical data for <b>{ticker}</b> on {parsed_date.strftime('%Y-%m-%d')}."}

    response_parts = []

    # A: OHLC / Price Queries
    if any(k in user_msg for k in ['open', 'close', 'high', 'low', 'price', 'ohlc']):
        d_str = target_date.strftime('%Y-%m-%d') if target_date else latest_date.strftime('%Y-%m-%d')
        lines = [f"Data for <b>{ticker}</b> on {d_str}:"]

        if 'open' in user_msg or 'ohlc' in user_msg or 'price' in user_msg:
            lines.append(f"• Open: {target_row['Open']:.2f}")
        if 'high' in user_msg or 'ohlc' in user_msg:
            lines.append(f"• High: {target_row['High']:.2f}")
        if 'low' in user_msg or 'ohlc' in user_msg:
            lines.append(f"• Low: {target_row['Low']:.2f}")
        if 'close' in user_msg or 'ohlc' in user_msg or 'price' in user_msg:
            lines.append(f"• Close: {target_row['Close']:.2f}")

        if len(lines) == 1:
            lines.append(f"• Close: {target_row['Close']:.2f}")

        response_parts.append("<br>".join(lines) + dashboard_msg)

    # B: Trend / Bull/Bear
    if any(k in user_msg for k in ['trend', 'bull', 'bear', 'analysis']):
        response_parts.append(f"<b>Trend Analysis:</b><br>• {analyze_trend(hist)}")

    # C: 52-Week High/Low
    if '52 week' in user_msg or 'year high' in user_msg or 'year low' in user_msg:
        # If we are here, needs_history=True, so hist has 5y data
        one_year = hist.tail(252)
        high_52 = one_year['High'].max()
        low_52 = one_year['Low'].min()
        response_parts.append(
            f"<b>52-Week Range ({ticker}):</b><br>• High: {high_52:.2f}<br>• Low: {low_52:.2f}"
        )

    # D: Fallback
    if not response_parts:
        return {"response": f"Found data for <b>{ticker}</b>, but unsure what to check. Try 'Closing price', 'Trend', or 'Predict {ticker} [date]'."}

    return {"response": "<br><br>".join(response_parts)}