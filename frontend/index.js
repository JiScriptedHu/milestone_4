// ==========================================
// CONFIG & STATE
// ==========================================
const API_BASE_URL = "http://127.0.0.1:8000/api/market";

let chartInstance = null;
let currentData = [];
let processedData = [];
let currentChartType = 'area';

// ==========================================
// INITIALIZATION
// ==========================================
window.onload = () => {
    if (!localStorage.getItem('stockUser')) {
        window.location.href = 'login.html';
        return;
    }

    document.querySelector('.logout-btn').addEventListener('click', () => {
        localStorage.removeItem('stockUser');
        window.location.href = 'login.html';
    });

    document.getElementById('searchInput').addEventListener('keydown', e => {
        if (e.key === 'Enter') handleSearch();
    });

    fetchStock("INFY.NS");
};

// ==========================================
// DATA FETCHING
// ==========================================
async function fetchStock(ticker) {
    try {
        const response = await fetch(`${API_BASE_URL}/${ticker}`);
        if (!response.ok) throw new Error("Stock not found");

        const result = await response.json();
        currentData = result.data;

        if (!currentData || currentData.length < 2)
            throw new Error("Insufficient data");

        processedData = currentData.map(item => ({
            ...item,
            timestamp: new Date(item.date).getTime()
        }));

        updateDashboardInfo(result);

        const activePeriod = document.querySelector('.time-selector button.active')?.innerText || '1Y';
        renderChart(activePeriod);

        document.getElementById('searchInput').value = '';

    } catch (error) {
        console.error("Fetch Error:", error);
        alert("Error fetching stock data. Please check the ticker.");
    }
}

function handleSearch() {
    const ticker = document.getElementById('searchInput').value.trim();
    if (ticker) fetchStock(ticker);
}

// ==========================================
// UI UPDATE
// ==========================================
function updateDashboardInfo(apiResult) {
    const latest = currentData.at(-1);
    const prev = currentData.at(-2);
    const currency = apiResult.currency || 'USD';

    setText('fullName', apiResult.name || '--');
    setText('tickerSymbol', apiResult.ticker || '--');
    setText('exchangeBadge', apiResult.exchange || 'MARKET');
    setText('dataDate', formatDate(latest.date));

    setText('currentPrice', `${currency} ${latest.close.toFixed(2)}`);

    const change = latest.close - prev.close;
    const pct = (change / prev.close) * 100;
    const changeEl = document.getElementById('priceChange');
    changeEl.innerText = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${pct.toFixed(2)}%)`;
    changeEl.style.color = change >= 0 ? '#00C805' : '#FF5000';

    setText('openPrice', `${currency} ${latest.open.toFixed(2)}`);
    setText('highPrice', `${currency} ${latest.high.toFixed(2)}`);
    setText('lowPrice', `${currency} ${latest.low.toFixed(2)}`);
    setText('volume', latest.volume.toLocaleString());
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function formatDate(d) {
    return new Date(d).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

// ==========================================
// CHART CONTROLS
// ==========================================
function setChartType(type) {
    currentChartType = type;

    document.getElementById('btnLine').className = type === 'area' ? 'active' : '';
    document.getElementById('btnCandle').className = type === 'candlestick' ? 'active' : '';

    const activePeriod = document.querySelector('.time-selector button.active')?.innerText || '1Y';
    renderChart(activePeriod);
}

function updateChartPeriod(period, el) {
    if (el) {
        document.querySelectorAll('.time-selector button').forEach(btn => btn.classList.remove('active'));
        el.classList.add('active');
    }
    renderChart(period);
}

// ==========================================
// CHART RENDERING
// ==========================================
function renderChart(period) {
    if (!processedData.length) return;

    let days = period === '1M' ? 30 : period === '5Y' ? 365 * 5 : 365;
    const count = Math.min(processedData.length, Math.floor(days * 0.7));
    const sliced = processedData.slice(-count);

    const start = sliced[0].close;
    const end = sliced.at(-1).close;
    const trendColor = end >= start ? '#00C805' : '#FF5000';

    const seriesData = sliced.map(item =>
        currentChartType === 'candlestick'
            ? { x: item.timestamp, y: [item.open, item.high, item.low, item.close] }
            : { x: item.timestamp, y: item.close }
    );

    if (chartInstance) chartInstance.destroy();

    const options = {
        series: [{ data: seriesData }],
        chart: {
            type: currentChartType,
            height: '100%',
            width: '100%',
            parentHeightOffset: 0,
            toolbar: { show: false },
            zoom: { enabled: false },
            animations: { enabled: false },
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        },
        colors: [trendColor],
        stroke: { width: currentChartType === 'area' ? 2 : 1, curve: 'straight' },
        fill: currentChartType === 'area'
            ? { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0, stops: [0, 100] } }
            : { type: 'solid' },
        grid: { borderColor: '#f1f1f1', padding: { top: 0, right: 40, bottom: 30, left: 10 } },
        xaxis: {
            type: 'datetime',
            labels: { style: { colors: '#999', fontSize: '11px' }, hideOverlappingLabels: true, offsetY: -5 },
            axisBorder: { show: false },
            axisTicks: { show: false }
        },
        yaxis: {
            opposite: true,
            labels: { style: { colors: '#999', fontSize: '11px' }, formatter: v => v.toFixed(0), offsetX: -10 }
        },
        dataLabels: { enabled: false },
        plotOptions: { candlestick: { colors: { upward: '#00C805', downward: '#FF5000' } } }
    };

    chartInstance = new ApexCharts(document.querySelector("#stockChart"), options);
    chartInstance.render();
}

// ==========================================
// SHORTCUTS
// ==========================================
document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }
});