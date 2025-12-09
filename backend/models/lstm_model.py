import os
import joblib
import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import tensorflow as tf

# Suppress TensorFlow warnings
tf.get_logger().setLevel('ERROR')


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


def build_model(input_shape):
    """Build and compile LSTM model."""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        LSTM(50, return_sequences=False),
        Dense(25),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def prepare_data(data, prediction_days):
    """Scale data and prepare sequences for LSTM training."""
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    x_train, y_train = [], []
    for i in range(prediction_days, len(scaled_data)):
        x_train.append(scaled_data[i - prediction_days:i, 0])
        y_train.append(scaled_data[i, 0])

    x_train = np.array(x_train).reshape((len(x_train), prediction_days, 1))
    y_train = np.array(y_train)

    return x_train, y_train, scaler, scaled_data


def train_model(x_train, y_train, input_shape):
    """Train LSTM model for one epoch."""
    model = build_model(input_shape)
    model.fit(x_train, y_train, batch_size=32, epochs=1, verbose=0)
    return model


def make_prediction(model, scaler, last_sequence, days_forecast, prediction_days):
    """Recursive prediction for future days."""
    future_outputs = []
    current_batch = last_sequence.reshape((1, prediction_days, 1))

    for _ in range(days_forecast):
        pred_scaled = model.predict(current_batch, verbose=0)[0]
        future_outputs.append(pred_scaled)
        current_batch = np.append(current_batch[:, 1:, :], [[pred_scaled]], axis=1)

    return scaler.inverse_transform(future_outputs).flatten().tolist()


# -----------------------------
# LSTM Prediction Function
# -----------------------------
def predict_lstm(df: pd.DataFrame, days_forecast: int = 7, ticker: str = ""):
    """
    Predict future stock prices using LSTM.

    Parameters:
        df (pd.DataFrame): DataFrame with ['date', 'close']
        days_forecast (int): Number of days to forecast
        ticker (str): Optional ticker symbol for caching

    Returns:
        dict: {"forecast": [...], "metrics": {...}}
    """
    try:
        data = df['close'].values.reshape(-1, 1)
        prediction_days = 60

        if len(data) < prediction_days + 20:
            return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}

        # Ensure 'date' column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        last_close_date = df['date'].iloc[-1].strftime('%Y-%m-%d')
        target_date = (df['date'].iloc[-1] + timedelta(days=days_forecast)).strftime('%Y-%m-%d')
        file_path = None

        final_model, metrics, scaler, scaled_data = None, None, None, None

        # -----------------------------
        # Cache Handling
        # -----------------------------
        if ticker:
            model_dir = os.path.join(os.path.dirname(__file__), 'lstm')
            os.makedirs(model_dir, exist_ok=True)
            file_name = f"{ticker}_lstm_{last_close_date}_{target_date}.pkl"
            file_path = os.path.join(model_dir, file_name)

            if os.path.exists(file_path):
                try:
                    cached = joblib.load(file_path)
                    weights = cached.get('weights')
                    metrics = cached.get('metrics')

                    # Reconstruct model for prediction
                    x_train, _, scaler, scaled_data = prepare_data(data, prediction_days)
                    input_shape = (x_train.shape[1], 1)
                    final_model = build_model(input_shape)
                    final_model.set_weights(weights)
                except Exception as e:
                    print(f"LSTM Cache Error: {e}")
                    final_model = None

        # -----------------------------
        # Training (if not cached)
        # -----------------------------
        if final_model is None or metrics is None:
            # Validation metrics
            validation_size = 14
            train_val = data[:-validation_size]
            test_val = data[-validation_size:]

            x_val, y_val, scaler_val, scaled_val = prepare_data(train_val, prediction_days)
            val_model = train_model(x_val, y_val, (x_val.shape[1], 1))
            last_seq_val = scaled_val[-prediction_days:]
            val_preds = make_prediction(val_model, scaler_val, last_seq_val, validation_size, prediction_days)
            metrics = calculate_metrics(test_val.flatten(), np.array(val_preds))

            # Final training on full data
            x_train, y_train, scaler, scaled_data = prepare_data(data, prediction_days)
            final_model = train_model(x_train, y_train, (x_train.shape[1], 1))

            if file_path:
                joblib.dump({
                    'weights': final_model.get_weights(),
                    'metrics': metrics
                }, file_path)

        # -----------------------------
        # Forecast
        # -----------------------------
        if scaler is None:
            _, _, scaler, scaled_data = prepare_data(data, prediction_days)

        last_sequence = scaled_data[-prediction_days:]
        forecast = make_prediction(final_model, scaler, last_sequence, days_forecast, prediction_days)

        return {"forecast": forecast, "metrics": metrics}

    except Exception as e:
        print(f"LSTM Error: {e}")
        return {"forecast": [], "metrics": {"rmse": 0, "accuracy": 0}}