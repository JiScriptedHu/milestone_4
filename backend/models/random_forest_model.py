import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from datetime import timedelta

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

def train_random_forest(df, features, target):
    """Train Random Forest regressor on the given dataframe."""
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(df[features], df[target])
    return model

def forecast_random_forest(model, last_known_row, features, days):
    """Generate recursive forecasts using trained Random Forest model."""
    current_input_values = last_known_row.values
    predictions = []

    for _ in range(days):
        input_df = pd.DataFrame([current_input_values], columns=features)
        next_pred = model.predict(input_df)[0]
        predictions.append(float(next_pred))

        # Recursive Step: shift lags
        current_input_values = np.array([next_pred, current_input_values[0], current_input_values[1]])

    return predictions

# -----------------------------
# Main Prediction Function
# -----------------------------
def predict_random_forest(df: pd.DataFrame, days_forecast: int = 7, ticker: str = ""):
    """
    Predict future stock prices using lag-based Random Forest.
    """
    try:
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        df = df.sort_values('date')

        # Create lag features
        for i in range(1, 4):
            df[f'lag_{i}'] = df['close'].shift(i)

        features = [f'lag_{i}' for i in range(1, 4)]
        target = 'close'
        df = df.dropna()

        if len(df) < 30:
            return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}

        metrics, model_full = None, None

        # -----------------------------
        # Cache Setup
        # -----------------------------
        last_close_date = df['date'].iloc[-1].strftime('%Y-%m-%d')
        target_date = (df['date'].iloc[-1] + timedelta(days=days_forecast)).strftime('%Y-%m-%d')
        file_path = None

        if ticker:
            model_dir = os.path.join(os.path.dirname(__file__), 'random_forest')
            os.makedirs(model_dir, exist_ok=True)
            file_name = f"{ticker}_rf_{last_close_date}_{target_date}.pkl"
            file_path = os.path.join(model_dir, file_name)

            if os.path.exists(file_path):
                try:
                    cached = joblib.load(file_path)
                    model_full = cached.get('model')
                    metrics = cached.get('metrics')
                except Exception:
                    pass

        # -----------------------------
        # Training (if not cached)
        # -----------------------------
        if model_full is None or metrics is None:
            # Validation
            val_size = 14
            train_df = df.iloc[:-val_size]
            test_df = df.iloc[-val_size:]

            model_val = train_random_forest(train_df, features, target)
            last_train_row = train_df.iloc[-1][features]
            val_preds = forecast_random_forest(model_val, last_train_row, features, val_size)
            metrics = calculate_metrics(test_df['close'].values, val_preds)

            # Final training on full data
            model_full = train_random_forest(df, features, target)

            # Cache model
            if file_path:
                joblib.dump({'model': model_full, 'metrics': metrics}, file_path)

        # -----------------------------
        # Recursive Forecast
        # -----------------------------
        close_values = df['close'].values
        last_input_series = pd.Series([close_values[-1], close_values[-2], close_values[-3]], index=features)
        final_forecast = forecast_random_forest(model_full, last_input_series, features, days_forecast)

        return {"forecast": final_forecast, "metrics": metrics}

    except Exception as e:
        print(f"Random Forest Error: {e}")
        return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}