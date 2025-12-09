import os
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from datetime import timedelta

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_metrics(y_true, y_pred):
    """Compute RMSE and accuracy (100 - MAPE)."""
    try:
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        # Handle zero division for MAPE
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
            if np.isnan(mape) or np.isinf(mape):
                mape = 0
        accuracy = max(0, 100 - mape)
        return {"rmse": round(float(rmse), 2), "accuracy": round(float(accuracy), 2)}
    except Exception:
        return {"rmse": 0.0, "accuracy": 0.0}

def train_linear_regression(df, features, target):
    """Train Linear Regression model on the given dataframe."""
    model = LinearRegression()
    model.fit(df[features], df[target])
    return model

def forecast_linear_regression(model, last_known_diffs, last_close_price, features, days):
    """
    Generate recursive forecasts predicting PRICE CHANGES, then reconstructing price.
    """
    current_input_values = last_known_diffs.values
    current_price = last_close_price
    predictions = []

    for _ in range(days):
        # Predict the CHANGE (diff)
        input_df = pd.DataFrame([current_input_values], columns=features)
        next_diff = model.predict(input_df)[0]

        # Reconstruct the price
        next_price = current_price + next_diff
        predictions.append(float(next_price))

        # Recursive Step: Shift lags of the DIFFERENCE
        # [new_diff, old_lag_1, old_lag_2]
        current_input_values = np.array([next_diff, current_input_values[0], current_input_values[1]])
        
        # Update current price for next iteration
        current_price = next_price

    return predictions

# -----------------------------
# Main Prediction Function
# -----------------------------
def predict_linear_regression(df: pd.DataFrame, days_forecast: int = 7, ticker: str = ""):
    """
    Predict future stock prices using Linear Regression on Differenced Data.
    """
    try:
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        df = df.sort_values('date')

        # 1. Feature Engineering: Use Differencing
        # We predict the 'change' instead of the raw 'close' to avoid flat-line predictions
        df['diff'] = df['close'].diff()

        # Create lags of the DIFFERENCE
        for i in range(1, 4):
            df[f'lag_{i}'] = df['diff'].shift(i)

        features = [f'lag_{i}' for i in range(1, 4)]
        target = 'diff' # Target is the change, not the price
        
        # Drop NaNs created by diff and shifting
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
            model_dir = os.path.join(os.path.dirname(__file__), 'linear_regression')
            os.makedirs(model_dir, exist_ok=True)
            file_name = f"{ticker}_linear_{last_close_date}_{target_date}_v2.pkl"
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
            # Validation Split
            val_size = 14
            train_df = df.iloc[:-val_size]
            test_df = df.iloc[-val_size:]

            # Train on 'diff'
            model_val = train_linear_regression(train_df, features, target)
            
            # Forecast validation
            last_train_diffs = train_df.iloc[-1][features]
            last_train_price = train_df.iloc[-1]['close']
            
            val_preds = forecast_linear_regression(
                model_val, last_train_diffs, last_train_price, features, val_size
            )
            
            # Compare reconstructed prices with actual test prices
            metrics = calculate_metrics(test_df['close'].values, val_preds)

            # Final training on full data
            model_full = train_linear_regression(df, features, target)

            # Cache model
            if file_path:
                joblib.dump({'model': model_full, 'metrics': metrics}, file_path)

        # -----------------------------
        # Recursive Forecast
        # -----------------------------
        # Prepare inputs for forecasting
        last_diff_row = df.iloc[-1][features]
        last_close_price = df.iloc[-1]['close']

        final_forecast = forecast_linear_regression(
            model_full, last_diff_row, last_close_price, features, days_forecast
        )

        return {"forecast": final_forecast, "metrics": metrics}

    except Exception as e:
        print(f"Linear Regression Error: {e}")
        return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}