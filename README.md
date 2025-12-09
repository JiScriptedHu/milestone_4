# Infosys Stock AI - Stock Analysis & Prediction Dashboard

A comprehensive Stock Market Analysis tool built with FastAPI that leverages multiple Machine Learning models (LSTM, XGBoost, Prophet) to forecast stock prices and visualize market trends.

## Key Features

* **Multi-Model Forecasting**: Compare predictions using Linear Regression, Random Forest, LSTM (Deep Learning), XGBoost, Prophet, and ARIMA.
* **Interactive Dashboard**: Real-time stock data visualization, OHLC metrics, and dynamic charts (Line/Candlestick) powered by ApexCharts and yfinance.
* **AI Chat Assistant**: A built-in chatbot capable of answering natural language queries about prices, trends, and simple predictions.
* **Secure Authentication**: User signup and login system utilizing Argon2 password hashing.

## How to Use

### Prerequisites
Ensure you have Python 3.9+ installed.

### 1. Navigate to the backend directory
Open your terminal and move to the backend folder where the python files are located:
```bash
cd milestone_4/backend
```

### 2. Allow script execution (Windows PowerShell)
```bash
Set-ExecutionPolicy Unrestricted -Scope Process
```

### 3. Create the virtual environment
```bash
python -m venv venv
```

### 4. Activate the environment
```bash
.\venv\Scripts\activate
```

### 5. Install the required dependencies
```bash
pip install -r requirements.txt
```

### 6. Run the Backend Server
Start the FastAPI server using Uvicorn:
```bash
uvicorn main:app --reload
```

The API will start at `http://127.0.0.1:8000`

### 7. Launch the Frontend
Since the frontend is built with static HTML/JS, you can simply navigate to the `milestone_4/frontend` folder and open `login.html` in your web browser.

**Note**: For the best experience, it is recommended to serve the frontend using a simple HTTP server:
```bash
# Open a new terminal in milestone_4/frontend
python -m http.server 5500
# Then go to http://localhost:5500/login.html
```

## Tech Stack

- **Backend**: FastAPI, Python
- **Machine Learning**: LSTM, XGBoost, Prophet, ARIMA, scikit-learn
- **Data**: yfinance
- **Frontend**: HTML, JavaScript, ApexCharts
- **Security**: Argon2 password hashing

<img width="1920" height="1020" alt="Screenshot 2025-12-09 172922" src="https://github.com/user-attachments/assets/53fa166c-05ab-441b-ac0d-4176e037a6c5" />

<img width="1920" height="1020" alt="Screenshot 2025-12-09 173722" src="https://github.com/user-attachments/assets/9dd06f07-737f-4cee-aa2e-c6b2dc228dfe" />

