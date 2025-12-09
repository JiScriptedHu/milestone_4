from fastapi import APIRouter, HTTPException, Query
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import traceback
import yfinance as yf
import pandas as pd

# -----------------------------
# Environment & Logging Setup
# -----------------------------
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow logs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress Prophet/Plotly warnings
logging.getLogger("prophet.plot").setLevel(logging.CRITICAL)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

# -----------------------------
# Model Registry
# -----------------------------
MODELS = {
    "lstm": {"func": None, "error": None},
    "xgboost": {"func": None, "error": None},
    "prophet": {"func": None, "error": None},
    "arima": {"func": None, "error": None},
    "tft": {"func": None, "error": None},
    "linear_regression": {"func": None, "error": None},
    "random_forest": {"func": None, "error": None},
}

# Load models safely
try:
    from models.lstm_model import predict_lstm
    MODELS["lstm"]["func"] = predict_lstm
except ImportError as e:
    MODELS["lstm"]["error"] = "TensorFlow/Keras not installed"
    logger.warning(f"LSTM unavailable: {e}")

try:
    from models.xgboost_model import predict_xgboost
    MODELS["xgboost"]["func"] = predict_xgboost
except ImportError as e:
    MODELS["xgboost"]["error"] = "XGBoost not installed"
    logger.warning(f"XGBoost unavailable: {e}")

try:
    from models.prophet_model import predict_prophet
    MODELS["prophet"]["func"] = predict_prophet
except ImportError as e:
    MODELS["prophet"]["error"] = "Prophet not installed"
    logger.warning(f"Prophet unavailable: {e}")

try:
    from models.arima_model import predict_arima
    MODELS["arima"]["func"] = predict_arima
except ImportError as e:
    MODELS["arima"]["error"] = "Statsmodels/ARIMA not installed"
    logger.warning(f"ARIMA unavailable: {e}")

try:
    from models.linear_regression_model import predict_linear_regression
    MODELS["linear_regression"]["func"] = predict_linear_regression
except ImportError as e:
    MODELS["linear_regression"]["error"] = "Scikit-learn not installed"
    logger.warning(f"Linear Regression unavailable: {e}")

try:
    from models.random_forest_model import predict_random_forest
    MODELS["random_forest"]["func"] = predict_random_forest
except ImportError as e:
    MODELS["random_forest"]["error"] = "Scikit-learn not installed"
    logger.warning(f"Random Forest unavailable: {e}")

# -----------------------------
# Router & Executor
# -----------------------------
router = APIRouter()
executor = ThreadPoolExecutor(max_workers=3)

# -----------------------------
# Helper Functions
# -----------------------------
def fetch_historical_data(ticker: str) -> pd.DataFrame:
    """Fetches last 2 years of historical data for a ticker."""
    try:
        logger.info(f"Fetching training data for {ticker}...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2y", auto_adjust=True)
        if hist.empty:
            logger.warning(f"No data found for {ticker}")
            return pd.DataFrame()

        hist.reset_index(inplace=True)
        if 'Date' in hist.columns:
            hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
        hist.columns = [c.lower() for c in hist.columns]

        if 'date' not in hist.columns or 'close' not in hist.columns:
            return pd.DataFrame()

        return hist[['date', 'close']]
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def run_model(model_name: str, df: pd.DataFrame, days: int, ticker: str):
    """Runs the specified model on historical data."""
    model_info = MODELS.get(model_name)
    if not model_info:
        raise ValueError("Invalid model name")

    if model_info["func"] is None:
        raise ImportError(model_info["error"] or "Model library missing")

    if df.empty or len(df) < 60:
        raise ValueError("Insufficient historical data (need 60+ days)")

    try:
        logger.info(f"Running {model_name} for {days} days on {ticker}...")
        # Model functions accept (df, days, ticker) for consistency
        result = model_info["func"](df, days, ticker=ticker)
        return result
    except Exception as e:
        logger.error(f"Runtime error in {model_name}: {e}")
        traceback.print_exc()
        raise RuntimeError(f"Model execution failed: {str(e)}")

# -----------------------------
# API Endpoint
# -----------------------------
@router.get("/{model_name}/{ticker}")
async def get_prediction(model_name: str, ticker: str, days: int = 7):
    """
    Predict future stock prices using specified model.
    - model_name: lstm, xgboost, prophet, arima, tft
    - ticker: stock symbol
    - days: number of days to forecast (default 7)
    """
    model_name = model_name.lower()
    if model_name not in MODELS:
        raise HTTPException(status_code=400, detail="Invalid model name")

    try:
        loop = asyncio.get_event_loop()
        # Fetch historical data asynchronously
        df = await loop.run_in_executor(executor, fetch_historical_data, ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {ticker}")

        # Run model asynchronously
        try:
            result = await loop.run_in_executor(executor, run_model, model_name, df, days, ticker)
        except ImportError as ie:
            raise HTTPException(status_code=501, detail=str(ie))
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

        if not result or not result.get('forecast'):
            raise HTTPException(status_code=500, detail=f"{model_name} returned no predictions.")

        return {
            "model": model_name,
            "ticker": ticker.upper(),
            "forecast": result['forecast'],
            "metrics": result.get('metrics', {"rmse": 0, "accuracy": 0})
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))