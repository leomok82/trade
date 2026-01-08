import { useState, useEffect, useCallback } from 'react';
import { Search, TrendingUp, TrendingDown, Settings, X, Save, RefreshCcw } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import './index.css';

const TIME_FRAMES = [
  { label: '1D', value: '1D', type: 'minutes', amount: 60 * 24 },
  { label: '1W', value: '1W', type: 'minutes', amount: 60 * 24 * 7 },
  { label: '1M', value: '1M', type: 'daily', amount: 30 },
  { label: '6M', value: '6M', type: 'daily', amount: 30 * 6 },
  { label: '1Y', value: '1Y', type: 'daily', amount: 365 },
];

function StockCard({ id, symbol, initialTimeframe, onRemove, onUpdate, setShowSettings }) {
  const [timeframe, setTimeframe] = useState(initialTimeframe || TIME_FRAMES[2]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    // Sync local timeframe change to parent for persistence
    onUpdate(id, { timeframe });
  }, [timeframe, id]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        let url;
        if (timeframe.type === 'minutes') {
          url = `http://localhost:5077/bars/minutes/${symbol}?minutes=${timeframe.amount}`;
        } else {
          url = `http://localhost:5077/bars/daily/${symbol}?days=${timeframe.amount}`;
        }

        const res = await fetch(url);
        if (res.status === 401) {
          setShowSettings(true);
          throw new Error("Please enter your API Key and Secret in Settings.");
        }
        if (!res.ok) throw new Error(`Failed to fetch ${symbol}`);

        const rawData = await res.json();

        // Format for Recharts
        const formatted = rawData.map(item => ({
          time: new Date(item.time).toLocaleString(), // for debugging
          displayTime: new Date(item.time).toLocaleString('en-US', {
            month: 'short', day: 'numeric',
            hour: timeframe.type === 'minutes' ? '2-digit' : undefined,
            minute: timeframe.type === 'minutes' ? '2-digit' : undefined,
          }),
          price: item.price
        }));

        setData(formatted);
      } catch (err) {
        if (!err.message.includes("Please enter your API Key")) {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, timeframe, setShowSettings, refreshTick]);

  // Derived metrics
  const currentPrice = data.length > 0 ? data[data.length - 1].price : null;
  const startPrice = data.length > 0 ? data[0].price : null;
  const priceChange = (currentPrice && startPrice) ? (currentPrice - startPrice) : 0;
  const percentChange = (currentPrice && startPrice) ? ((priceChange / startPrice) * 100) : 0;
  const isPositive = priceChange >= 0;

  return (
    <div style={{
      border: '1px solid #dfe1e5',
      borderRadius: '8px',
      padding: '20px',
      marginBottom: '20px',
      backgroundColor: 'white',
      position: 'relative'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '15px' }}>
          <h3 style={{ margin: 0, color: '#202124', fontSize: '1.2rem' }}>{symbol}</h3>
          {!loading && !error && currentPrice && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                ${currentPrice.toFixed(2)}
              </span>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                color: isPositive ? '#0F9D58' : '#DB4437',
                fontWeight: '500',
                fontSize: '0.9rem'
              }}>
                {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                <span style={{ marginLeft: '4px' }}>
                  {isPositive ? '+' : ''}{percentChange.toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '5px' }}>
            {TIME_FRAMES.map((tf) => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '12px',
                  backgroundColor: timeframe.value === tf.value ? '#e8f0fe' : 'transparent',
                  color: timeframe.value === tf.value ? '#1967d2' : '#5f6368',
                  fontSize: '0.8rem',
                  fontWeight: '500',
                  border: '1px solid transparent',
                }}
              >
                {tf.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setRefreshTick(prev => prev + 1)}
            style={{ color: '#5f6368', padding: '5px', marginLeft: '5px', display: 'flex', alignItems: 'center' }}
            title="Refresh data"
            disabled={loading}
          >
            <RefreshCcw size={18} className={loading ? 'animate-spin' : ''} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          </button>
          <button
            onClick={() => onRemove(id)}
            style={{ color: '#5f6368', padding: '5px', marginLeft: '5px' }}
            title="Remove chart"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      <div style={{ height: '200px', width: '100%' }}>
        {loading && <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#5f6368' }}>Loading...</div>}

        {error && <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#DB4437' }}>{error}</div>}

        {!loading && !error && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid vertical={false} stroke="#e0e0e0" strokeDasharray="3 3" />
              <XAxis dataKey="displayTime" tick={{ fill: '#9aa0a6', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#e0e0e0' }} minTickGap={30} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#9aa0a6', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }} />
              <Line type="monotone" dataKey="price" stroke={isPositive ? '#0F9D58' : '#DB4437'} strokeWidth={2} dot={false} activeDot={{ r: 6 }} animationDuration={400} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}


function App() {
  const [charts, setCharts] = useState(() => {
    try {
      const saved = localStorage.getItem('stock_charts');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [query, setQuery] = useState('');

  // Settings state
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');

  useEffect(() => {
    localStorage.setItem('stock_charts', JSON.stringify(charts));
  }, [charts]);

  const addSymbol = (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Allow multiple comma-separated
    const newSyms = query.split(',')
      .map(s => s.trim().toUpperCase())
      .filter(s => s);

    const newCharts = newSyms.map(sym => ({
      id: Date.now() + Math.random().toString(), // simple unique id
      symbol: sym,
      timeframe: TIME_FRAMES[2] // default 1M
    }));

    setCharts(prev => [...newCharts, ...prev]); // Add to top
    setQuery('');
  };

  const removeChart = (id) => {
    setCharts(charts.filter(c => c.id !== id));
  };

  const updateChart = useCallback((id, updates) => {
    setCharts(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c));
  }, []);

  const saveCredentials = async () => {
    if (!apiKey || !apiSecret) {
      alert("Please enter both key and secret.");
      return;
    }

    try {
      const res = await fetch('http://localhost:5077/settings/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: apiKey, secret: apiSecret })
      });

      if (res.ok) {
        setShowSettings(false);
        setApiKey('');
        setApiSecret('');
      } else {
        const text = await res.text();
        alert("Error saving: " + text);
      }
    } catch (err) {
      console.error(err);
      alert("Network error saving credentials.");
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'Inter, sans-serif', backgroundColor: '#f8f9fa' }}>

      {/* Sidebar */}
      <div style={{
        width: '300px',
        backgroundColor: 'white',
        borderRight: '1px solid #dfe1e5',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        top: 0,
        bottom: 0,
        left: 0,
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '30px', paddingLeft: '10px' }}>
          <TrendingUp size={28} color="#4285F4" />
          <span style={{ fontSize: '1.2rem', fontWeight: '800', letterSpacing: '1px' }}>STONKS</span>
        </div>

        <form onSubmit={addSymbol} style={{ marginBottom: '20px' }}>
          <div style={{
            border: '1px solid #dfe1e5',
            borderRadius: '8px',
            padding: '10px',
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'white'
          }}>
            <Search color="#9aa0a6" size={18} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Add symbol (e.g. AAPL)"
              style={{
                border: 'none',
                outline: 'none',
                flex: 1,
                marginLeft: '10px',
                fontSize: '14px'
              }}
            />
          </div>
          <button type="submit" style={{ display: 'none' }}>Add</button>
        </form>

        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '0.85rem', color: '#5f6368', paddingLeft: '5px' }}>
            Enter a symbol above and press Enter to add a chart to the dashboard.
          </p>
        </div>

        <button
          onClick={() => setShowSettings(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px',
            borderRadius: '8px',
            color: '#5f6368',
            backgroundColor: 'transparent',
            marginTop: 'auto',
            cursor: 'pointer',
            textAlign: 'left'
          }}
          onMouseEnter={e => e.currentTarget.style.backgroundColor = '#f1f3f4'}
          onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
        >
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: '40px', marginLeft: '300px', maxWidth: '1000px' }}>
        {charts.length === 0 ? (
          <div style={{
            height: '70vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            color: '#9aa0a6'
          }}>
            <TrendingUp size={48} style={{ marginBottom: '20px', opacity: 0.5 }} />
            <p>No charts yet. Add a symbol from the sidebar.</p>
          </div>
        ) : (
          <div style={{ animation: 'fadeIn 0.3s' }}>
            {charts.map(chart => (
              <StockCard
                key={chart.id}
                {...chart}
                initialTimeframe={chart.timeframe}
                onRemove={removeChart}
                onUpdate={updateChart}
                setShowSettings={setShowSettings}
              />
            ))}
          </div>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => setShowSettings(false)}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '400px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            position: 'relative'
          }} onClick={e => e.stopPropagation()}>

            <h3 style={{ margin: '0 0 20px 0', fontSize: '1.25rem' }}>Alpaca API Settings</h3>

            <button
              onClick={() => setShowSettings(false)}
              style={{
                position: 'absolute',
                top: '15px',
                right: '15px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#5f6368'
              }}
            >
              <X size={20} />
            </button>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', color: '#5f6368' }}>API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #dfe1e5',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>

            <div style={{ marginBottom: '25px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', color: '#5f6368' }}>API Secret</label>
              <input
                type="password"
                value={apiSecret}
                onChange={e => setApiSecret(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #dfe1e5',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>

            <button
              onClick={saveCredentials}
              style={{
                width: '100%',
                padding: '10px',
                backgroundColor: '#1a73e8',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <Save size={18} />
              Save Credentials
            </button>

            <p style={{ marginTop: '15px', fontSize: '0.8rem', color: '#5f6368', textAlign: 'center' }}>
              Credentials are stored securely on your machine.
            </p>

          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export default App;
