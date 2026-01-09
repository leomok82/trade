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
        const symbols = symbol.split(',').map(s => s.trim().toUpperCase());

        if (symbols.length === 1) {
          // Single symbol format
          const formatted = rawData.map(item => ({
            time: new Date(item.time).toLocaleString(),
            displayTime: new Date(item.time).toLocaleString('en-US', {
              month: 'short', day: 'numeric',
              hour: timeframe.type === 'minutes' ? '2-digit' : undefined,
              minute: timeframe.type === 'minutes' ? '2-digit' : undefined,
            }),
            [symbols[0]]: item.price,
            price: item.price // for single symbol metrics
          }));
          setData(formatted);
        } else {
          // Multiple symbols dictionary format
          // Need to align timestamps. For simplicity, we assume they are roughly aligned or we key by timestamp.
          const allTimes = new Set();
          Object.values(rawData).forEach(bars => {
            bars.forEach(b => allTimes.add(b.time));
          });

          const sortedTimes = Array.from(allTimes).sort();
          const timestampToData = {};
          sortedTimes.forEach(t => {
            timestampToData[t] = {
              time: t,
              displayTime: new Date(t).toLocaleString('en-US', {
                month: 'short', day: 'numeric',
                hour: timeframe.type === 'minutes' ? '2-digit' : undefined,
                minute: timeframe.type === 'minutes' ? '2-digit' : undefined,
              })
            };
          });

          Object.entries(rawData).forEach(([sym, bars]) => {
            bars.forEach(b => {
              if (timestampToData[b.time]) {
                timestampToData[b.time][sym] = b.price;
              }
            });
          });

          const formatted = Object.values(timestampToData);
          setData(formatted);
        }
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

  // Derived metrics for single symbol
  const symbols = symbol.split(',').map(s => s.trim().toUpperCase());
  const isMulti = symbols.length > 1;
  const mainSym = symbols[0];

  const currentPrice = (data.length > 0 && !isMulti) ? data[data.length - 1][mainSym] : null;
  const startPrice = (data.length > 0 && !isMulti) ? data[0][mainSym] : null;
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
          {!loading && !error && currentPrice != null && !isMulti && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                ${Number(currentPrice).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                  {isPositive ? '+' : ''}{(percentChange || 0).toFixed(2)}%
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
              {symbols.map((s, idx) => (
                <Line
                  key={s}
                  type="monotone"
                  dataKey={s}
                  stroke={idx === 0 ? (isMulti ? '#4285F4' : (isPositive ? '#0F9D58' : '#DB4437')) : ['#DB4437', '#0F9D58', '#F4B400', '#4285F4'][idx % 4]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                  animationDuration={400}
                />
              ))}
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
  const [portfolio, setPortfolio] = useState({ netValue: 0, investments: {}, pnlPercent: 0, realizedPnL: 0, currentPrices: {} });
  const [txSymbol, setTxSymbol] = useState('');
  const [txQty, setTxQty] = useState('');
  const [txPrice, setTxPrice] = useState('');
  const [txBuy, setTxBuy] = useState(true);
  const [holdingOrder, setHoldingOrder] = useState([]); // Array of symbols for ordering

  // Settings state
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');

  useEffect(() => {
    localStorage.setItem('stock_charts', JSON.stringify(charts));
  }, [charts]);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:5077/portfolio/pnl');
      if (res.ok) {
        const data = await res.json();
        // Normalize casing if needed
        const normalized = {
          netValue: data.netValue ?? 0,
          investments: data.investments ?? {},
          pnlPercent: data.pnLPercent ?? data.pnlPercent ?? 0,
          realizedPnL: data.realizedPnL ?? 0,
          currentPrices: data.currentPrices ?? {}
        };
        setPortfolio(normalized);

        // Update holding order if new symbols appear
        const symbols = Object.keys(normalized.investments);
        setHoldingOrder(prev => {
          const existing = new Set(prev);
          const newOnes = symbols.filter(s => !existing.has(s));
          const stillThere = prev.filter(s => normalized.investments[s]);
          return [...stillThere, ...newOnes];
        });
      }
    } catch (err) {
      console.error("Failed to fetch portfolio", err);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, [fetchPortfolio]);

  const addSymbol = (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const sym = query.trim().toUpperCase();
    const newChart = {
      id: Date.now() + Math.random().toString(),
      symbol: sym,
      timeframe: TIME_FRAMES[2]
    };

    setCharts(prev => [newChart, ...prev]);
    setQuery('');
  };

  const removeChart = (id) => {
    setCharts(charts.filter(c => c.id !== id));
  };

  const updateChart = useCallback((id, updates) => {
    setCharts(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c));
  }, []);

  const submitTransaction = async (e) => {
    e.preventDefault();
    if (!txSymbol || !txQty || !txPrice) return;

    const tx = {
      symbol: txSymbol.toUpperCase(),
      quantity: parseInt(txQty),
      transactionPrice: parseFloat(txPrice),
      transactionDate: new Date().toISOString(),
      buy: txBuy
    };

    try {
      const res = await fetch('http://localhost:5077/portfolio/transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tx)
      });
      if (res.ok) {
        fetchPortfolio();
        setTxSymbol('');
        setTxQty('');
        setTxPrice('');
      } else {
        const errText = await res.text();
        alert(errText);
      }
    } catch (err) {
      alert("Network error submitting transaction");
    }
  };

  const resetPortfolio = async () => {
    if (!window.confirm("Are you sure you want to reset your portfolio?")) return;
    try {
      const res = await fetch('http://localhost:5077/portfolio/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (res.ok) {
        fetchPortfolio();
      } else {
        const text = await res.text();
        alert("Reset failed: " + text);
      }
    } catch (err) {
      alert("Error resetting portfolio");
    }
  };

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
        width: '400px',
        backgroundColor: 'white',
        borderRight: '1px solid #dfe1e5',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        top: 0,
        bottom: 0,
        left: 0,
        zIndex: 10,
        overflowX: 'hidden',
        overflowY: 'auto'
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

        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px' }}>
          <p style={{ fontSize: '0.85rem', color: '#5f6368', paddingLeft: '5px' }}>
            Enter symbols to compare performance.
          </p>

          {/* Portfolio Section */}
          <div style={{ marginTop: '30px', borderTop: '1px solid #dfe1e5', paddingTop: '20px' }}>
            <h4 style={{ margin: '0 0 15px 5px', fontSize: '0.9rem', color: '#202124' }}>Portfolio Management</h4>
            <div style={{
              backgroundColor: '#f8f9fa',
              padding: '12px',
              borderRadius: '8px',
              marginBottom: '15px',
              fontSize: '0.85rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', alignItems: 'center' }}>
                <span style={{ color: '#5f6368', fontWeight: '500' }}>Portfolio PnL:</span>
                <span style={{
                  fontSize: '1.1rem',
                  fontWeight: '700',
                  color: (portfolio.pnlPercent || 0) >= 0 ? '#0F9D58' : '#DB4437',
                  backgroundColor: (portfolio.pnlPercent || 0) >= 0 ? '#e6f4ea' : '#fce8e6',
                  padding: '4px 8px',
                  borderRadius: '4px'
                }}>
                  {(portfolio.pnlPercent || 0) >= 0 ? '+' : ''}{(portfolio.pnlPercent || 0).toFixed(2)}%
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
                <span style={{ color: '#5f6368', fontWeight: '500' }}>Realized PnL:</span>
                <span style={{
                  fontWeight: '600',
                  color: (portfolio.realizedPnL || 0) >= 0 ? '#0F9D58' : '#DB4437',
                  fontSize: '0.9rem'
                }}>
                  {(portfolio.realizedPnL || 0) >= 0 ? '+' : ''}${(portfolio.realizedPnL || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '15px' }}>
                <button
                  onClick={fetchPortfolio}
                  style={{
                    flex: 1,
                    padding: '6px',
                    fontSize: '0.75rem',
                    borderRadius: '4px',
                    border: '1px solid #dfe1e5',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px'
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = '#f8f9fa'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'white'}
                >
                  <RefreshCcw size={14} /> Refresh
                </button>
                <button
                  onClick={resetPortfolio}
                  style={{
                    flex: 1,
                    padding: '6px',
                    fontSize: '0.75rem',
                    borderRadius: '4px',
                    border: '1px solid #fce8e6',
                    backgroundColor: '#fff',
                    color: '#DB4437',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = '#fef7f6'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = '#fff'}
                >
                  Reset
                </button>
              </div>

              <div style={{ marginTop: '20px' }}>
                <span style={{ color: '#5f6368', display: 'block', marginBottom: '10px', fontSize: '0.85rem', fontWeight: '500' }}>Current Holdings:</span>
                {holdingOrder.length === 0 ? (
                  <span style={{ fontStyle: 'italic', color: '#9aa0a6', padding: '10px', display: 'block' }}>No holdings</span>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {holdingOrder.map((sym, index) => {
                      const inv = portfolio.investments[sym];
                      if (!inv) return null;
                      const price = portfolio.currentPrices[sym] || 0;
                      const pnl = (price - inv.averageCost) * inv.quantity;
                      const pnlPct = inv.averageCost > 0 ? ((price - inv.averageCost) / inv.averageCost * 100) : 0;
                      const isHoldingPos = pnl >= 0;

                      return (
                        <div
                          key={sym}
                          draggable
                          onDragStart={(e) => {
                            e.dataTransfer.setData('symbol', sym);
                            e.currentTarget.style.opacity = '0.5';
                          }}
                          onDragEnd={(e) => e.currentTarget.style.opacity = '1'}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={(e) => {
                            e.preventDefault();
                            const draggedSym = e.dataTransfer.getData('symbol');
                            if (draggedSym === sym) return;
                            setHoldingOrder(prev => {
                              const newOrder = [...prev];
                              const draggedIdx = newOrder.indexOf(draggedSym);
                              const targetIdx = newOrder.indexOf(sym);
                              newOrder.splice(draggedIdx, 1);
                              newOrder.splice(targetIdx, 0, draggedSym);
                              return newOrder;
                            });
                          }}
                          style={{
                            backgroundColor: 'white',
                            border: '1px solid #dfe1e5',
                            borderRadius: '8px',
                            padding: '12px',
                            cursor: 'grab',
                            transition: 'all 0.2s ease',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                          }}
                          onMouseEnter={e => {
                            e.currentTarget.style.borderColor = '#4285F4';
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(66, 133, 244, 0.1)';
                          }}
                          onMouseLeave={e => {
                            e.currentTarget.style.borderColor = '#dfe1e5';
                            e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <div>
                              <div style={{ fontWeight: '700', fontSize: '1rem', color: '#202124' }}>{sym}</div>
                              <div style={{ fontSize: '0.75rem', color: '#5f6368' }}>{inv.quantity} shares @ ${inv.averageCost.toFixed(2)}</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{
                                fontWeight: '700',
                                color: isHoldingPos ? '#0F9D58' : '#DB4437',
                                fontSize: '0.9rem'
                              }}>
                                {isHoldingPos ? '+' : ''}${pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                              </div>
                              <div style={{ fontSize: '0.7rem', color: isHoldingPos ? '#0F9D58' : '#DB4437', opacity: 0.8 }}>
                                {isHoldingPos ? '+' : ''}{pnlPct.toFixed(2)}%
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px', marginTop: '10px', borderTop: '1px solid #f1f3f4', paddingTop: '10px' }}>
                            <div style={{ flex: 1, fontSize: '0.75rem', color: '#5f6368' }}>
                              Price: <span style={{ fontWeight: '600', color: '#202124' }}>${price.toFixed(2)}</span>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setTxSymbol(sym);
                                setTxQty(inv.quantity.toString());
                                setTxPrice(price.toFixed(2));
                                setTxBuy(false);
                                // Scroll to form
                                document.getElementById('tx-form')?.scrollIntoView({ behavior: 'smooth' });
                              }}
                              style={{
                                padding: '4px 12px',
                                borderRadius: '4px',
                                border: '1px solid #fce8e6',
                                backgroundColor: '#fff',
                                color: '#DB4437',
                                fontSize: '0.7rem',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'all 0.1s'
                              }}
                              onMouseEnter={e => e.currentTarget.style.backgroundColor = '#fce8e6'}
                              onMouseLeave={e => e.currentTarget.style.backgroundColor = '#fff'}
                            >
                              Sell All
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <form id="tx-form" onSubmit={submitTransaction} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input
                placeholder="Symbol"
                value={txSymbol}
                onChange={e => setTxSymbol(e.target.value)}
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #dfe1e5', fontSize: '0.85rem' }}
              />
              <input
                placeholder="Qty"
                type="number"
                value={txQty}
                onChange={e => setTxQty(e.target.value)}
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #dfe1e5', fontSize: '0.85rem' }}
              />
              <input
                placeholder="Price"
                type="number"
                step="0.01"
                value={txPrice}
                onChange={e => setTxPrice(e.target.value)}
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #dfe1e5', fontSize: '0.85rem' }}
              />
              <div style={{ display: 'flex', gap: '5px' }}>
                <button
                  type="button"
                  onClick={() => setTxBuy(true)}
                  style={{
                    flex: 1, padding: '6px', borderRadius: '4px', cursor: 'pointer',
                    backgroundColor: txBuy ? '#0F9D58' : '#fff',
                    color: txBuy ? '#fff' : '#5f6368',
                    border: '1px solid #dfe1e5',
                    fontSize: '0.8rem'
                  }}
                >Buy</button>
                <button
                  type="button"
                  onClick={() => setTxBuy(false)}
                  style={{
                    flex: 1, padding: '6px', borderRadius: '4px', cursor: 'pointer',
                    backgroundColor: !txBuy ? '#DB4437' : '#fff',
                    color: !txBuy ? '#fff' : '#5f6368',
                    border: '1px solid #dfe1e5',
                    fontSize: '0.8rem'
                  }}
                >Sell</button>
              </div>
              <button
                type="submit"
                style={{
                  backgroundColor: '#1a73e8', color: '#fff', border: 'none',
                  padding: '8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '500'
                }}
              >Submit Transaction</button>
            </form>
          </div>
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
      <div style={{ flex: 1, padding: '40px', marginLeft: '400px', maxWidth: 'calc(100% - 400px)' }}>
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
