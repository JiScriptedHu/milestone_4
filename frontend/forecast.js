const API_MARKET_URL = "http://127.0.0.1:8000/api/market";
const API_PREDICT_URL = "http://127.0.0.1:8000/api/predict";

let historicalChartInstance = null;
let modelChartInstances = [];

// ==========================
// Initialization
// ==========================
window.onload = () => {
    if (!localStorage.getItem('stockUser')) {
        window.location.href = 'login.html';
        return;
    }

    const today = new Date();
    const futureDate = new Date(today);
    futureDate.setDate(today.getDate() + 14);

    const dateInput = document.getElementById('targetDate');
    if (dateInput) {
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);
        dateInput.min = tomorrow.toISOString().split('T')[0];
        dateInput.value = futureDate.toISOString().split('T')[0];
    }

    const tickerInput = document.getElementById('forecastTicker');
    if (tickerInput && tickerInput.value) {
        fetchStockHeader(tickerInput.value).then(history => {
            if (history) renderHistoricalChart(history);
        });
    }
};

// ==========================
// Logout
// ==========================
const logoutBtn = document.querySelector('.logout-btn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('stockUser');
        window.location.href = 'login.html';
    });
}

// ==========================
// Fetch Stock Header
// ==========================
async function fetchStockHeader(ticker) {
    try {
        const res = await fetch(`${API_MARKET_URL}/${ticker}`);
        if (!res.ok) return null;
        const data = await res.json();

        setText('fullName', data.name || ticker);
        setText('tickerSymbol', data.ticker || ticker);
        setText('exchangeBadge', data.exchange || 'MARKET');

        if (data.data && data.data.length > 1) {
            const latest = data.data[data.data.length - 1];
            const prev = data.data[data.data.length - 2];
            const change = latest.close - prev.close;
            const pct = (change / prev.close) * 100;

            setText('currentPrice', latest.close.toFixed(2));
            
            // UPDATED: Use formatDate helper to match dashboard style
            setText('dataDate', formatDate(latest.date));

            const changeEl = document.getElementById('priceChange');
            if (changeEl) {
                changeEl.innerHTML = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${pct.toFixed(2)}%)`;
                changeEl.style.color = change >= 0 ? '#00C805' : '#FF5000';
            }

            return data.data;
        }
        return null;
    } catch (e) {
        console.error("Header fetch error", e);
        return null;
    }
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

// NEW: Standard Date Formatter
function formatDate(d) {
    return new Date(d).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

// ==========================
// Helper: Calculate SMA
// ==========================
function calculateSMA(data, window) {
    let sma = [];
    for (let i = 0; i < data.length; i++) {
        if (i < window - 1) {
            sma.push(null);
            continue;
        }
        let sum = 0;
        for (let j = 0; j < window; j++) {
            sum += data[i - j].close;
        }
        sma.push({
            x: new Date(data[i].date).getTime(),
            y: parseFloat((sum / window).toFixed(2))
        });
    }
    return sma.filter(p => p !== null);
}

// ==========================
// Run Forecast
// ==========================
async function runForecast() {
    const tickerInput = document.getElementById('forecastTicker');
    const dateInput = document.getElementById('targetDate');
    if (!tickerInput || !dateInput) return;

    const ticker = tickerInput.value.trim();
    const targetDateStr = dateInput.value;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const targetDate = new Date(targetDateStr);
    const diffTime = targetDate - today;
    const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (!ticker || days < 1) {
        alert("Please enter a valid ticker and a future date.");
        return;
    }

    const checkboxes = document.querySelectorAll('input[name="model"]:checked');
    const selectedModels = Array.from(checkboxes).map(cb => cb.value);

    if (selectedModels.length === 0) {
        alert("Select at least one model.");
        return;
    }

    setLoading(true);

    try {
        const historyData = await fetchStockHeader(ticker);
        if (!historyData) throw new Error("Could not fetch historical data. Check ticker.");

        renderHistoricalChart(historyData);

        const promises = selectedModels.map(async (model) => {
            try {
                const res = await fetch(`${API_PREDICT_URL}/${model}/${ticker}?days=${days}`);
                const data = await res.json();
                if (!res.ok) {
                    return { model, error: data.detail || "Unknown error" };
                }
                return data;
            } catch (err) {
                return { model, error: "Network Error" };
            }
        });

        const results = await Promise.all(promises);
        const successResults = results.filter(r => !r.error);
        const errorResults = results.filter(r => r.error);

        if (successResults.length === 0 && errorResults.length > 0) {
            alert(`All models failed.\n${errorResults.map(e => `${e.model}: ${e.error}`).join('\n')}`);
        }

        renderMetricCards(successResults, errorResults, historyData[historyData.length - 1].close);
        renderModelForecasts(historyData, successResults);

    } catch (error) {
        alert(error.message);
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    const btn = document.getElementById('predictBtn');
    const resultsContainer = document.getElementById('forecastResults');
    const modelsContainer = document.getElementById('modelChartsContainer');

    if (isLoading) {
        btn.disabled = true;
        btn.querySelector('.loader').style.display = 'block';
        btn.querySelector('.btn-text').style.display = 'none';
        document.getElementById('loadingMessage').style.display = 'flex';
        if (resultsContainer) resultsContainer.innerHTML = '';
        if (modelsContainer) modelsContainer.innerHTML = '';
    } else {
        btn.disabled = false;
        btn.querySelector('.loader').style.display = 'none';
        btn.querySelector('.btn-text').style.display = 'block';
        document.getElementById('loadingMessage').style.display = 'none';
    }
}

// ==========================
// Render Metric Cards
// ==========================
function renderMetricCards(successResults, errorResults, lastClose) {
    const container = document.getElementById('forecastResults');
    if (!container) return;
    container.innerHTML = '';

    successResults.forEach(res => {
        if (!res.forecast || res.forecast.length === 0) return;

        const finalPrice = res.forecast[res.forecast.length - 1];
        const change = ((finalPrice - lastClose) / lastClose) * 100;
        const color = change >= 0 ? '#00C805' : '#FF5000';
        const rmse = res.metrics ? res.metrics.rmse : 'N/A';
        const accuracy = res.metrics ? res.metrics.accuracy + '%' : 'N/A';

        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
            <p class="label" style="color:${getColorForModel(res.model)}">${res.model.toUpperCase()}</p>
            <div class="metric-value-large">${finalPrice.toFixed(2)}</div>
            <p class="data" style="color: ${color}; font-weight:700;">
                ${change >= 0 ? '▲' : '▼'} ${Math.abs(change).toFixed(2)}%
            </p>
            <div style="margin-top:10px; font-size:11px; color:#666;">
                RMSE: <strong>${rmse}</strong><br>
                Confidence: <strong>${accuracy}</strong>
            </div>
        `;
        container.appendChild(card);
    });

    errorResults.forEach(err => {
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.style.borderLeft = "4px solid #FF5000";
        card.innerHTML = `
            <p class="label" style="color:#666;">${err.model.toUpperCase()}</p>
            <div class="metric-value-large" style="font-size: 16px; color: #FF5000;">FAILED</div>
            <p class="data" style="font-size: 12px; margin-top:5px; color:#333;">${err.error}</p>
        `;
        container.appendChild(card);
    });
}

// ==========================
// Chart Renderers
// ==========================
function renderHistoricalChart(history) {
    const chartEl = document.querySelector("#historicalChart");
    if (!chartEl) return;

    if (historicalChartInstance) historicalChartInstance.destroy();

    const prices = history.map(item => ({ x: new Date(item.date).getTime(), y: item.close }));
    const ma50 = calculateSMA(history, 50);
    const ma100 = calculateSMA(history, 100);

    const options = {
        series: [
            { name: "Close Price", type: 'area', data: prices },
            { name: "MA 50", type: 'line', data: ma50 },
            { name: "MA 100", type: 'line', data: ma100 }
        ],
        chart: { height: '100%', type: 'line', toolbar: { show: false }, fontFamily: 'inherit', animations: { enabled: false }, zoom: { enabled: false } },
        stroke: { width: [2, 2, 2], curve: 'straight', dashArray: [0, 0, 0] },
        fill: { type: ['gradient', 'solid', 'solid'], gradient: { opacityFrom: 0.4, opacityTo: 0.1 } },
        colors: ['#6C757D', '#2962ff', '#ff6d00'],
        xaxis: { type: 'datetime', tickAmount: 15, labels: { show: true, rotate: -45, style: { fontSize: '11px' }, format: 'dd MMM' } },
        yaxis: { labels: { formatter: val => val.toFixed(0) } },
        grid: { borderColor: '#f1f1f1', padding: { top: 0, right: 20, bottom: 50, left: 20 } },
        legend: { position: 'top' },
        title: { text: 'Price History & Moving Averages', align: 'left', style: { fontSize: '14px' } }
    };

    historicalChartInstance = new ApexCharts(chartEl, options);
    historicalChartInstance.render();
}

function renderModelForecasts(history, results) {
    const container = document.getElementById('modelChartsContainer');
    if (!container) return;

    modelChartInstances.forEach(chart => chart.destroy());
    modelChartInstances = [];
    container.innerHTML = '';

    const contextDays = 60;
    const recentHistory = history.slice(-contextDays);
    const lastDate = new Date(recentHistory[recentHistory.length - 1].date);

    results.forEach(res => {
        if (!res.forecast || res.forecast.length === 0) return;

        const rmse = res.metrics ? res.metrics.rmse : '0.00';
        const accuracy = res.metrics ? res.metrics.accuracy : '0.00';

        const cardDiv = document.createElement('div');
        cardDiv.className = 'model-chart';
        cardDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h4 style="margin:0; text-transform:uppercase; color:${getColorForModel(res.model)}; font-size:12px; font-weight:700;">
                    ${res.model} Prediction
                </h4>
                <div style="font-size:10px; color:#666; text-align:right;">
                    RMSE: <b>${rmse}</b> | Acc: <b>${accuracy}%</b>
                </div>
            </div>
            <div class="model-chart-div"></div>
        `;
        container.appendChild(cardDiv);
        const chartDiv = cardDiv.querySelector('.model-chart-div');

        const historySeries = recentHistory.map(item => ({ x: new Date(item.date).getTime(), y: item.close }));

        const forecastData = [{ x: lastDate.getTime(), y: recentHistory[recentHistory.length - 1].close }];
        res.forecast.forEach((price, idx) => {
            const nextDate = new Date(lastDate);
            nextDate.setDate(lastDate.getDate() + (idx + 1));
            forecastData.push({ x: nextDate.getTime(), y: price });
        });

        const options = {
            series: [
                { name: "History", data: historySeries },
                { name: "Forecast", data: forecastData }
            ],
            chart: { height: '100%', type: 'line', toolbar: { show: false }, fontFamily: 'inherit', zoom: { enabled: false } },
            colors: ['#999', getColorForModel(res.model)],
            stroke: { width: [1, 3], curve: 'smooth', dashArray: [0, 4] },
            xaxis: { type: 'datetime', labels: { show: true, format: 'dd MMM' }, tickAmount: 6 },
            yaxis: { labels: { formatter: val => val.toFixed(2) } },
            tooltip: { y: { formatter: val => val.toFixed(2) } },
            grid: { borderColor: '#f1f1f1', padding: { left: 10, right: 10, bottom: 20 } },
            legend: { show: false }
        };

        const chart = new ApexCharts(chartDiv, options);
        chart.render();
        modelChartInstances.push(chart);
    });
}

// ==========================
// Helper: Model Colors
// ==========================
function getColorForModel(modelName) {
    const colors = {
        'lstm': '#6200ea',
        'prophet': '#00bfa5',
        'xgboost': '#ff6d00',
        'arima': '#2962ff',
        'tft': '#d50000',
        'linear_regression': '#d500f9',
        'random_forest': '#00c853'
    };
    return colors[modelName] || '#333';
}