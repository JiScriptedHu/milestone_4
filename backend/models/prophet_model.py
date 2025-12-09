import os
import joblib
import logging
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_squared_error
from datetime import timedelta

# Suppress unnecessary logging
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)


# -----------------------------
# Helper Functions
# -----------------------------
def calculate_metrics(y_true, y_pred):
    """Compute RMSE and accuracy (100 - MAPE)."""
    try:
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        accuracy = max(0, 100 - mape)
        return {"rmse": round(float(rmse), 2), "accuracy": round(float(accuracy), 2)}
    except Exception:
        return {"rmse": 0.0, "accuracy": 0.0}


def train_prophet(df: pd.DataFrame):
    """Train a Prophet model on given dataframe."""
    model = Prophet(daily_seasonality=True)
    model.fit(df)
    return model


def make_forecast(model, days: int):
    """Generate forecast for the next `days` using a trained Prophet model."""
    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)
    return forecast.tail(days)['yhat'].values


# -----------------------------
# Prophet Prediction Function
# -----------------------------
def predict_prophet(df: pd.DataFrame, days_forecast: int = 7, ticker: str = ""):
    """
    Predict future stock prices using Prophet.

    Parameters:
        df (pd.DataFrame): DataFrame with ['date', 'close']
        days_forecast (int): Number of days to forecast
        ticker (str): Optional ticker symbol for caching

    Returns:
        dict: {"forecast": [...], "metrics": {...}}
    """
    try:
        # Prepare data for Prophet
        prophet_df = df[['date', 'close']].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds']).dt.tz_localize(None)

        if len(prophet_df) < 30:
            return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}

        final_model, metrics = None, None

        # -----------------------------
        # Cache Setup
        # -----------------------------
        last_close_date = prophet_df['ds'].iloc[-1].strftime('%Y-%m-%d')
        target_date = (prophet_df['ds'].iloc[-1] + timedelta(days=days_forecast)).strftime('%Y-%m-%d')
        file_path = None

        if ticker:
            model_dir = os.path.join(os.path.dirname(__file__), 'prophet')
            os.makedirs(model_dir, exist_ok=True)
            file_name = f"{ticker}_prophet_{last_close_date}_{target_date}.pkl"
            file_path = os.path.join(model_dir, file_name)

            if os.path.exists(file_path):
                try:
                    cached = joblib.load(file_path)
                    final_model = cached.get('model')
                    metrics = cached.get('metrics')
                except Exception as e:
                    print(f"Prophet cache load failed: {e}")

        # -----------------------------
        # Training (if not cached)
        # -----------------------------
        if final_model is None or metrics is None:
            # Validation
            val_size = 14
            train_df = prophet_df.iloc[:-val_size]
            test_df = prophet_df.iloc[-val_size:]

            val_model = train_prophet(train_df)
            val_preds = make_forecast(val_model, val_size)
            metrics = calculate_metrics(test_df['y'].values, val_preds)

            # Final training on full data
            final_model = train_prophet(prophet_df)

            # Cache model
            if file_path:
                joblib.dump({'model': final_model, 'metrics': metrics}, file_path)

        # -----------------------------
        # Forecast
        # -----------------------------
        forecast_values = make_forecast(final_model, days_forecast)

        return {"forecast": forecast_values.tolist(), "metrics": metrics}

    except Exception as e:
        print(f"Prophet Error: {e}")
        return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}