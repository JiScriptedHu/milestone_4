import os
import warnings
import joblib
import pandas as pd
import numpy as np
from datetime import timedelta
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_metrics(y_true, y_pred):
    """Calculate RMSE and accuracy (100 - MAPE)."""
    try:
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        accuracy = max(0, 100 - mape)
        return {"rmse": round(float(rmse), 2), "accuracy": round(float(accuracy), 2)}
    except Exception:
        return {"rmse": 0.0, "accuracy": 0.0}

# -----------------------------
# ARIMA Prediction
# -----------------------------
def predict_arima(df: pd.DataFrame, days_forecast: int = 7, ticker: str = ""):
    """
    Predict future stock prices using ARIMA.

    Parameters:
        df (pd.DataFrame): DataFrame with columns ['date', 'close']
        days_forecast (int): Number of days to forecast
        ticker (str): Optional ticker symbol for caching

    Returns:
        dict: {"forecast": [...], "metrics": {...}}
    """
    warnings.filterwarnings("ignore")

    try:
        if len(df) < 30:
            return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}

        # Ensure 'date' column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        data = df['close'].values
        last_close_date = df['date'].iloc[-1].strftime('%Y-%m-%d')
        target_date_obj = df['date'].iloc[-1] + timedelta(days=days_forecast)
        target_date = target_date_obj.strftime('%Y-%m-%d')

        # -----------------------------
        # Cache Setup
        # -----------------------------
        file_path = None
        model_fit, metrics = None, None
        if ticker:
            model_dir = os.path.join(os.path.dirname(__file__), 'arima')
            os.makedirs(model_dir, exist_ok=True)
            file_name = f"{ticker}_arima_{last_close_date}_{target_date}.pkl"
            file_path = os.path.join(model_dir, file_name)

            if os.path.exists(file_path):
                try:
                    cached = joblib.load(file_path)
                    model_fit = cached.get('model')
                    metrics = cached.get('metrics')
                except Exception as e:
                    print(f"Failed to load ARIMA cache: {e}")

        # -----------------------------
        # Train Model if Cache Missing
        # -----------------------------
        if model_fit is None or metrics is None:
            # Validation metrics (Train/Test split)
            val_size = 14
            train_data, test_data = data[:-val_size], data[-val_size:]

            val_model = ARIMA(train_data, order=(5, 1, 0)).fit()
            val_preds = val_model.forecast(steps=val_size)
            metrics = calculate_metrics(test_data, val_preds)

            # Final Training on full data
            model_fit = ARIMA(data, order=(5, 1, 0)).fit()

            # Save to cache
            if file_path:
                joblib.dump({'model': model_fit, 'metrics': metrics}, file_path)

        # -----------------------------
        # Forecast Future Values
        # -----------------------------
        forecast_output = model_fit.forecast(steps=days_forecast)

        return {"forecast": forecast_output.tolist(), "metrics": metrics}

    except Exception as e:
        print(f"ARIMA Error: {e}")
        return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}