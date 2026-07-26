import React, { useState, useEffect, useMemo } from 'react';
import { 
  LineChart, Search, TrendingUp, TrendingDown, Activity, Globe, Newspaper,
  ChevronRight, Bell, Menu, Sparkles, Filter, Plus, Check, ListOrdered, 
  RefreshCw, AlertTriangle, Loader2, Star, Briefcase, X, PieChart,
  ArrowUpRight, ArrowDownRight
} from 'lucide-react';

const globalStyles = `
  @keyframes water-ripple {
    0% { transform: translate(-50%, -50%) scale(0); opacity: 0.4; }
    100% { transform: translate(-50%, -50%) scale(4); opacity: 0; }
  }
  .water-ripple-effect {
    position: fixed; border-radius: 50%;
    background: radial-gradient(circle, rgba(168,85,247,0.4) 0%, rgba(168,85,247,0) 70%);
    pointer-events: none; z-index: 9999; width: 150px; height: 150px;
    animation: water-ripple 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
  }
  @keyframes pulse-slow {
    0%, 100% { opacity: 0.65; transform: scale(1); }
    50% { opacity: 0.95; transform: scale(1.05); }
  }
  @keyframes nav-ripple {
    0% { transform: translate(-50%, -50%) scale(0); opacity: 1; }
    100% { transform: translate(-50%, -50%) scale(4); opacity: 0; }
  }
  @keyframes slide-up {
    0% { transform: translateY(100%); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
  }
  .animate-slide-up { animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
  
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(99, 102, 241, 0.2);
    border-radius: 10px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background-color: rgba(99, 102, 241, 0.4);
  }
`;

const parseCSV = (csvText) => {
  const cleanText = csvText.replace(/\r/g, ''); 
  const lines = cleanText.trim().split('\n');
  if (lines.length < 2) return [];
  
  const headers = lines[0].split(',').map(h => h.replace(/^"|"$/g, '').trim());
  const results = [];
  
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
    const obj = {};
    headers.forEach((header, index) => {
      let val = row[index] ? row[index].replace(/^"|"$/g, '').trim() : null;
      if (val !== null && val !== '' && !isNaN(val)) {
        val = Number(val);
      }
      obj[header] = val;
    });
    results.push(obj);
  }
  return results;
};

// Pearson Correlation Math Function
const getPearsonCorrelation = (x, y) => {
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
  const minLength = Math.min(x.length, y.length);
  if (minLength === 0) return 0;
  
  for (let i = 0; i < minLength; i++) {
    sumX += x[i];
    sumY += y[i];
    sumXY += x[i] * y[i];
    sumX2 += x[i] * x[i];
    sumY2 += y[i] * y[i];
  }
  
  const step1 = (minLength * sumXY) - (sumX * sumY);
  const step2 = (minLength * sumX2) - (sumX * sumX);
  const step3 = (minLength * sumY2) - (sumY * sumY);
  const step4 = Math.sqrt(step2 * step3);
  
  if (step4 === 0) return 0;
  return step1 / step4;
};

const S3_BUCKET_URL = "https://lumina-strategies.s3.ca-central-1.amazonaws.com";
const LAMBDA_WATCHLIST_URL = "https://gksj5d66m3h2yrwotmgrcsielm0yddth.lambda-url.ca-central-1.on.aws/"; 
const LAMBDA_RESEARCH_URL = "https://cm4bsrcjx6m5skhbhl3ciwjory0jbwam.lambda-url.ca-central-1.on.aws/";
const LAMBDA_FAVORITES_URL = "https://cvci7hcm3iaj6dwf3gyrcv6izq0xsmez.lambda-url.ca-central-1.on.aws/";

const INDEXES = [
  { id: 'sp500', name: 'S&P 500' },
  { id: 'sp400', name: 'S&P 400' },
  { id: 'sp600', name: 'S&P 600' },
  { id: 'tsx', name: 'TSX' }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [savedStocks, setSavedStocks] = useState([]);
  const [watchList, setWatchList] = useState([]); 
  
  const [liveData, setLiveData] = useState([]);
  const [macroData, setMacroData] = useState([]);
  const [aiSentiment, setAiSentiment] = useState([{ sentiment: 'Analyzing...', confidence: '--', summary: 'Awaiting API...' }]);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [dataError, setDataError] = useState('');

  useEffect(() => {
    const fetchAllData = async () => {
      setIsLoadingData(true);
      setDataError('');
      let allParsedData = [];

      try {
        // 1. Fetch Stocks
        for (const index of INDEXES) {
          const fileUrl = `${S3_BUCKET_URL}/data/today/${index.id}_latest.csv`;
          try {
            const response = await fetch(fileUrl);
            if (!response.ok) continue;
            
            const csvText = await response.text();
            const rawData = parseCSV(csvText);
            
            const labeledData = rawData.map(row => ({
              ...row,
              Index_Source: index.name
            }));
            
            allParsedData = [...allParsedData, ...labeledData];
          } catch (err) {
            console.error(`[Pipeline ERROR] Failed to fetch ${index.id}:`, err);
          }
        }

        // 2. Fetch Global Macro
        try {
          const macroUrl = `${S3_BUCKET_URL}/data/macro/global_macro_latest.csv`;
          const macroRes = await fetch(macroUrl);
          if (macroRes.ok) {
            const macroText = await macroRes.text();
            setMacroData(parseCSV(macroText));
          }
        } catch (err) {
          console.warn("Macro data not found in S3 yet.", err);
        }

        // 3. Fetch Sentiment & Watchlist
        try {
          const sentimentUrl = `${S3_BUCKET_URL}/dashboard/sentiment/sentiment.json`;
          const sentResponse = await fetch(sentimentUrl);
          if (sentResponse.ok) {
            const sentData = await sentResponse.json();
            setAiSentiment(Array.isArray(sentData) ? sentData : [sentData]);
          }
        } catch (err) {}

        try {
          const watchlistUrl = `${S3_BUCKET_URL}/dashboard/watchlist/watchlist.json`;
          const watchResponse = await fetch(watchlistUrl);
          if (watchResponse.ok) {
            const watchData = await watchResponse.json();
            setWatchList(watchData);
          }
        } catch (err) {
          console.warn("No existing watchlist found in S3, starting fresh.");
        }

        // Process Stocks
        const groupedByTicker = {};
        allParsedData.forEach(row => {
          const ticker = row.Ticker;
          if (!ticker) return; 
          
          const close = row.close || row.Close_Price || 0;
          const target = row.target_mean || row.target_median || row.max_target || row.Target_Mean_Price || close;
          const company = row.Company || row.company || row.Company_Name || ticker; 
          const sector = row.sector || row.Sector || 'Unknown';
          const dateStr = row.date || row.Date || '2000-01-01';
          
          let indexSource = row.Index_Source || row.index || 'Unknown';
          if (indexSource === 'SP500') indexSource = 'S&P 500';
          if (indexSource === 'SP400') indexSource = 'S&P 400';
          if (indexSource === 'SP600') indexSource = 'S&P 600';

          if (!groupedByTicker[ticker]) {
            groupedByTicker[ticker] = {
              t: ticker, n: company, idx: indexSource, sec: sector, history: []
            };
          }
          
          groupedByTicker[ticker].history.push({
            ...row,
            Date: dateStr,
            Close_Price: close,
            Target_Mean_Price: target,
            Trailing_PE: row.trailingPE || row.Trailing_PE || 0,
            Market_Cap: row.Market_Cap || 0,
            Volume: row.Volume || row.volume || 0,
            Average_Volume: row.Average_Volume || row.averageVolume || 0
          });
        });

        const finalProcessedData = Object.values(groupedByTicker).map(stock => {
          stock.history.sort((a, b) => new Date(a.Date) - new Date(b.Date));
          const latestRecord = stock.history[stock.history.length - 1];
          
          const histClose = stock.history.map(record => record.Close_Price);
          const histTarget = stock.history.map(record => record.Target_Mean_Price || record.Close_Price);
          
          const close = latestRecord.Close_Price;
          const target = latestRecord.Target_Mean_Price || close; 
          const upside = close > 0 ? ((target - close) / close) * 100 : 0;

          return {
            ...stock,
            close,
            target,
            upside,
            peRatio: latestRecord.Trailing_PE || 0,
            marketCap: latestRecord.Market_Cap || 0,
            histClose,
            histTarget,
            latestRecord
          };
        });

        setLiveData(finalProcessedData);
      } catch (err) {
        setDataError('Failed to fetch from AWS S3.');
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchAllData();
  }, []);

  useEffect(() => {
    const handleGlobalClick = (e) => {
      if (e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('select')) return;
      const ripple = document.createElement('div');
      ripple.className = 'water-ripple-effect';
      ripple.style.left = `${e.clientX}px`;
      ripple.style.top = `${e.clientY}px`;
      document.body.appendChild(ripple);
      setTimeout(() => ripple.remove(), 800);
    };

    window.addEventListener('click', handleGlobalClick);
    const styleTag = document.createElement('style');
    styleTag.innerHTML = globalStyles;
    document.head.appendChild(styleTag);

    return () => {
      window.removeEventListener('click', handleGlobalClick);
      document.head.removeChild(styleTag);
    };
  }, []);

  const toggleSavedStock = (ticker) => {
    setSavedStocks(prev => 
      prev.includes(ticker) ? prev.filter(t => t !== ticker) : [...prev, ticker]
    );
  };

  const syncWatchlistToCloud = async (newList) => {
    try {
      const response = await fetch(LAMBDA_WATCHLIST_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watchlist: newList })
      });
      if (!response.ok) console.error("[Cloud Sync] AWS Server Error");
    } catch (err) {
      console.error("[Cloud Sync] Failed to reach AWS:", err);
    }
  };

  const toggleWatchList = (ticker) => {
    setWatchList(prev => {
      const newList = prev.includes(ticker) ? prev.filter(t => t !== ticker) : [...prev, ticker];
      syncWatchlistToCloud(newList);
      return newList;
    });
  };

  const movePipelineToWatchlist = () => {
    setWatchList(prev => {
      const newList = [...new Set([...prev, ...savedStocks])];
      syncWatchlistToCloud(newList);
      return newList;
    });
    setSavedStocks([]); 
    setActiveTab('portfolio'); 
  };

  return (
    <div className="min-h-screen bg-[#07050f] text-slate-200 font-sans selection:bg-blue-500/30 relative overflow-hidden">
      
      {/* Background Ambience */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#5b21b6]/55 rounded-full blur-[150px]" style={{ animation: 'pulse-slow 15s infinite alternate' }}></div>
        <div className="absolute top-[25%] left-[15%] w-[45%] h-[55%] bg-[#1e40af]/60 rounded-full blur-[160px]" style={{ animation: 'pulse-slow 20s infinite alternate-reverse' }}></div>
        <div className="absolute bottom-[-15%] right-[-10%] w-[60%] h-[60%] bg-[#3730a3]/65 rounded-full blur-[150px]" style={{ animation: 'pulse-slow 18s infinite alternate' }}></div>
        <div className="absolute top-[45%] left-[45%] w-[30%] h-[30%] bg-[#6d28d9]/45 rounded-full blur-[120px]"></div>
      </div>

      {/* Sidebar Navigation */}
      <nav className="fixed top-6 left-6 h-[calc(100vh-48px)] w-64 bg-[#0a1128]/85 border border-[#1e3a8a]/50 backdrop-blur-2xl rounded-3xl hidden md:flex flex-col z-10 shadow-2xl shadow-black/80">
        <div className="p-6 cursor-pointer" onClick={() => setActiveTab('home')}>
          <h1 className="text-xl font-serif font-semibold bg-gradient-to-br from-amber-100 via-amber-200 to-yellow-600 bg-clip-text text-transparent tracking-widest uppercase flex items-center gap-2 drop-shadow-md">
            <Sparkles size={20} className="text-amber-300" />
            Lumina
          </h1>
        </div>

        <div className="flex-1 px-4 space-y-2 mt-4">
          <NavItem icon={<Activity size={18} />} label="Macro Screener" active={activeTab === 'macro'} onClick={() => setActiveTab('macro')} />
          <NavItem icon={<Briefcase size={18} />} label="Portfolio Tracker" active={activeTab === 'portfolio'} onClick={() => setActiveTab('portfolio')} />
          <NavItem icon={<LineChart size={18} />} label="Target Analysis" active={activeTab === 'deep'} onClick={() => setActiveTab('deep')} />
          <NavItem icon={<Globe size={18} />} label="Economic Analysis" active={activeTab === 'bench'} onClick={() => setActiveTab('bench')} />
          <NavItem icon={<Newspaper size={18} />} label="AI News Engine" active={activeTab === 'news'} onClick={() => setActiveTab('news')} />
        </div>

        <div className="p-4 m-4 bg-[#111c38]/80 rounded-2xl border border-[#1e3a8a]/50 backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center font-bold text-white shadow-inner">B</div>
            <div>
              <p className="text-sm font-medium text-slate-200">System Admin</p>
              <p className="text-xs text-emerald-400 font-bold">● S3 Active</p>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="relative z-10 md:ml-[18rem] p-6 md:p-8 min-h-screen pb-24">
        
        {activeTab === 'macro' && (
          <header className="flex justify-between items-center mb-10 bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-4 rounded-3xl shadow-xl shadow-black/40 animate-slide-up">
            <div className="flex items-center md:hidden">
              <Menu className="text-slate-400 mr-4 cursor-pointer" />
              <h1 className="text-lg font-serif font-semibold bg-gradient-to-br from-amber-100 via-amber-200 to-yellow-600 bg-clip-text text-transparent tracking-widest uppercase drop-shadow-md">
                Lumina Strategies
              </h1>
            </div>
            
            <div className="hidden md:block relative w-96 ml-2">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-500" size={18} />
              <input 
                type="text" 
                placeholder="Ask Lumina Strategies or search assets..." 
                className="w-full bg-[#07050f]/90 border border-[#1e3a8a]/60 rounded-2xl py-2.5 pl-11 pr-4 text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all text-slate-200 shadow-inner placeholder-slate-600"
              />
            </div>

            <div className="flex items-center space-x-4 mr-2">
              <button className="p-2.5 bg-[#0a1128]/80 border border-[#1e3a8a]/50 rounded-xl hover:bg-[#111c38] transition-colors relative backdrop-blur-md">
                <Bell size={18} className="text-slate-400" />
                <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.8)]"></span>
              </button>
              <button className="text-sm bg-gradient-to-r from-purple-700 to-indigo-700 hover:from-purple-600 hover:to-indigo-600 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-[0_0_20px_rgba(126,34,206,0.3)] hover:shadow-[0_0_25px_rgba(126,34,206,0.5)] border border-purple-400/20">
                Run Pipeline
              </button>
            </div>
          </header>
        )}

        {isLoadingData && activeTab !== 'home' ? (
           <div className="flex flex-col items-center justify-center h-[60vh]">
             <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
             <h2 className="text-xl font-bold text-white mb-2">Connecting to AWS S3...</h2>
             <p className="text-slate-400">Fetching latest global market data pipeline.</p>
           </div>
        ) : dataError && activeTab !== 'home' ? (
           <div className="flex flex-col items-center justify-center h-[60vh] text-center">
             <AlertTriangle className="w-12 h-12 text-rose-500 mb-4" />
             <h2 className="text-xl font-bold text-white mb-2">Awaiting First AWS Run</h2>
             <p className="text-slate-400 max-w-md">No data found in S3 bucket.</p>
           </div>
        ) : (
          <>
            {activeTab === 'home' && (
              <DashboardHome 
                totalStocks={liveData.length} 
                data={liveData} 
                sentiment={aiSentiment} 
                savedStocks={savedStocks}
                toggleSaved={toggleSavedStock}
              />
            )}
            {activeTab === 'portfolio' && (
              <PortfolioTracker watchList={watchList} toggleWatchList={toggleWatchList} data={liveData} />
            )}
            {activeTab === 'macro' && (
              <MacroScreener data={liveData} savedStocks={savedStocks} toggleSaved={toggleSavedStock} />
            )}
            {activeTab === 'deep' && (
              <TargetAnalysis savedStocks={savedStocks} watchList={watchList} toggleWatchList={toggleWatchList} data={liveData} />
            )}
            {activeTab === 'bench' && (
              <EconomicAnalysis savedStocks={savedStocks} watchList={watchList} data={liveData} macroData={macroData} />
            )}
            {activeTab === 'news' && (
              <AINewsEngine savedStocks={savedStocks} watchList={watchList} data={liveData} />
            )}
          </>
        )}
      </main>

      {/* Floating Save Bar */}
      {savedStocks.length > 0 && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 ml-32 z-50 animate-slide-up">
          <div className="bg-[#0a1128]/95 backdrop-blur-2xl border border-blue-500/40 p-3 px-6 rounded-full shadow-[0_10px_40px_rgba(0,0,0,0.8)] flex items-center space-x-6">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-500/20 p-2 rounded-full border border-blue-500/30">
                <ListOrdered size={18} className="text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">{savedStocks.length} Stocks in Pipeline</p>
                <p className="text-[11px] text-blue-300">Ready for Analysis</p>
              </div>
            </div>
            <button 
              onClick={movePipelineToWatchlist}
              className="bg-amber-600/20 border border-amber-500/50 hover:bg-amber-600/40 text-amber-400 px-4 py-2 rounded-full text-sm font-bold transition-all flex items-center shadow-[0_0_15px_rgba(245,158,11,0.2)]">
              <Star size={16} className="mr-1.5" /> Save to Portfolio
            </button>
            <button 
              onClick={() => setActiveTab('deep')}
              className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2 rounded-full text-sm font-bold transition-all shadow-[0_0_15px_rgba(37,99,235,0.4)]">
              Target Analysis <ChevronRight size={16} className="inline ml-1" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================
// ECONOMIC ANALYSIS (MACRO CORRELATION ENGINE)
// ==========================================
function EconomicAnalysis({ savedStocks, watchList, data, macroData }) {
  const [selectedTicker, setSelectedTicker] = useState('');
  const [selectedMacro, setSelectedMacro] = useState('');
  const [timeframe, setTimeframe] = useState('180D');
  const [lagMonths, setLagMonths] = useState(0); // NEW: Time Lag State
  
  const [savedPlays, setSavedPlays] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const combinedAssets = useMemo(() => [...new Set([...savedStocks, ...watchList])], [savedStocks, watchList]);

  // Extract available macro columns (ignore Date)
  const availableMacros = useMemo(() => {
    if (!macroData || macroData.length === 0) return [];
    return Object.keys(macroData[0]).filter(k => k !== 'Date' && k !== 'index').sort();
  }, [macroData]);

  // Fetch saved plays from S3 on load
  useEffect(() => {
    const fetchSavedPlays = async () => {
      try {
        const response = await fetch(`${S3_BUCKET_URL}/dashboard/favorites/macro_favorites.json?t=${new Date().getTime()}`);
        if (response.ok) {
          const plays = await response.json();
          setSavedPlays(Array.isArray(plays) ? plays : []);
        }
      } catch (e) {
        console.log("No saved plays found or error fetching.");
      }
    };
    fetchSavedPlays();
  }, []);

  // Auto-select defaults
  useEffect(() => {
    if (combinedAssets.length > 0 && !selectedTicker) setSelectedTicker(combinedAssets[0]);
    if (availableMacros.length > 0 && !selectedMacro) {
      const defaultMetric = availableMacros.find(m => m.includes('Treasury') || m.includes('Yield')) || availableMacros[0];
      setSelectedMacro(defaultMetric);
    }
  }, [combinedAssets, availableMacros, selectedTicker, selectedMacro]);

  const stock = data.find(s => s.t === selectedTicker);
  
  // Align the Data with Time Lag Math
  const alignedData = useMemo(() => {
    if (!stock || !stock.history || macroData.length === 0 || !selectedMacro) return [];
    
    // Create a dictionary of macro dates for O(1) lookup
    const macroDict = {};
    macroData.forEach(row => {
      macroDict[row.Date] = row[selectedMacro];
    });

    let days = 30;
    if (timeframe === '60D') days = 60;
    if (timeframe === '90D') days = 90;
    if (timeframe === '180D') days = 180;
    if (timeframe === '1Y') days = 365;
    if (timeframe === 'MAX') days = 900; 

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);

    // Helper to shift date backward by X months safely
    const getLaggedDateStr = (dateStr, months) => {
      if (months === 0) return dateStr;
      const [y, m, d] = dateStr.split('-');
      const dateObj = new Date(y, m - 1, d);
      dateObj.setMonth(dateObj.getMonth() - months);
      const ny = dateObj.getFullYear();
      const nm = String(dateObj.getMonth() + 1).padStart(2, '0');
      const nd = String(dateObj.getDate()).padStart(2, '0');
      return `${ny}-${nm}-${nd}`;
    };

    const merged = [];
    stock.history.forEach(record => {
      const recDate = new Date(record.Date);
      if (recDate >= cutoff) {
        // Shift the macro lookup date backward in time to test for leading indicators
        const targetDateStr = getLaggedDateStr(record.Date, lagMonths);
        const macroVal = macroDict[targetDateStr];
        
        if (macroVal !== undefined && macroVal !== null) {
          merged.push({
            date: record.Date, // Keep true stock date for the x-axis alignment
            price: record.Close_Price,
            macro: macroVal
          });
        }
      }
    });

    return merged;
  }, [stock, macroData, selectedMacro, timeframe, lagMonths]);

  // Math & SVG Generation
  const chartProps = useMemo(() => {
    if (alignedData.length === 0) return null;

    const prices = alignedData.map(d => d.price);
    const macros = alignedData.map(d => d.macro);
    
    const pMin = Math.min(...prices) * 0.98;
    const pMax = Math.max(...prices) * 1.02;
    const mMin = Math.min(...macros) * 0.98;
    const mMax = Math.max(...macros) * 1.02;

    const pricePath = alignedData.map((d, i) => {
      const x = (i / (alignedData.length - 1)) * 100;
      const y = 100 - ((d.price - pMin) / (pMax - pMin)) * 100;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');

    const macroPath = alignedData.map((d, i) => {
      const x = (i / (alignedData.length - 1)) * 100;
      const y = 100 - ((d.macro - mMin) / (mMax - mMin)) * 100;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');

    const correlation = getPearsonCorrelation(prices, macros);
    
    // Labels
    const start = new Date(alignedData[0].date);
    const end = new Date(alignedData[alignedData.length - 1].date);
    const mid = new Date(start.getTime() + (end.getTime() - start.getTime()) / 2);
    
    const formatDt = (d) => {
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: timeframe === '1Y' || timeframe === 'MAX' ? '2-digit' : undefined });
    };

    return {
      pricePath, macroPath, pMin, pMax, mMin, mMax,
      correlation,
      labels: [formatDt(start), formatDt(mid), formatDt(end)],
      currPrice: prices[prices.length - 1],
      currMacro: macros[macros.length - 1],
      startPrice: prices[0],
      startMacro: macros[0]
    };

  }, [alignedData, timeframe]);

  const handleSavePlay = async () => {
    setIsSaving(true);
    const newPlay = { 
      id: Date.now().toString(),
      ticker: selectedTicker, 
      macro: selectedMacro, 
      timeframe: timeframe,
      lag: lagMonths, // Save the specific lag setting
      correlation: chartProps.correlation // Hard-save the exact correlation math
    };
    
    // Prevent exact duplicates
    if (savedPlays.some(p => p.ticker === newPlay.ticker && p.macro === newPlay.macro && p.timeframe === newPlay.timeframe && p.lag === newPlay.lag)) {
      setIsSaving(false);
      return;
    }

    const updatedPlays = [...savedPlays, newPlay];
    
    try {
      const res = await fetch(LAMBDA_FAVORITES_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ favorites: updatedPlays })
      });
      
      if (res.ok) {
        setSavedPlays(updatedPlays);
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
      }
    } catch (e) {
      console.error("Save failed:", e);
    }
    setIsSaving(false);
  };

  const removePlay = async (idToRemove) => {
    const updatedPlays = savedPlays.filter(p => p.id !== idToRemove);
    setSavedPlays(updatedPlays);
    try {
      await fetch(LAMBDA_FAVORITES_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ favorites: updatedPlays })
      });
    } catch (e) {}
  };

  if (macroData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-slide-up text-center">
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Syncing with FRED API...</h2>
        <p className="text-slate-400">Waiting for first macro data push to S3.</p>
      </div>
    );
  }

  if (combinedAssets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-slide-up text-center">
        <div className="w-24 h-24 rounded-full bg-[#111c38]/80 border border-blue-500/30 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(59,130,246,0.3)]">
          <Globe size={40} className="text-blue-400" />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">Macro Sync Active</h2>
        <p className="text-slate-400 max-w-md">120+ Global metrics loaded. Save a stock to your Portfolio or Pipeline to run correlation analysis.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl animate-slide-up">
      <div className="flex flex-col md:flex-row justify-between md:items-center bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-6 rounded-3xl shadow-xl shadow-black/40 gap-4">
        <div>
          <h2 className="text-2xl font-serif font-medium text-amber-50/90 tracking-wide flex items-center gap-3 drop-shadow-sm">
            <Globe size={24} className="text-blue-400/80" /> Global Macro Correlator
          </h2>
          <p className="text-sm text-slate-400 mt-1">Live dual-axis overlay analyzing asset reaction to {availableMacros.length} economic indicators.</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative">
            <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5 ml-1">Asset (Y1 Axis)</label>
            <select 
              className="w-full sm:w-40 bg-[#111c38]/90 border border-amber-500/50 rounded-xl px-4 py-2.5 text-sm text-amber-400 font-bold focus:outline-none focus:border-amber-400 shadow-inner appearance-none cursor-pointer"
              value={selectedTicker} onChange={(e) => setSelectedTicker(e.target.value)}
            >
              {combinedAssets.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <ChevronRight size={16} className="absolute right-4 bottom-3 text-amber-500 pointer-events-none rotate-90" />
          </div>
          
          <div className="relative">
            <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5 ml-1">Macro Metric (Y2 Axis)</label>
            <select 
              className="w-full sm:w-64 bg-[#111c38]/90 border border-blue-500/50 rounded-xl px-4 py-2.5 text-sm text-blue-400 font-bold focus:outline-none focus:border-blue-400 shadow-inner appearance-none cursor-pointer"
              value={selectedMacro} onChange={(e) => setSelectedMacro(e.target.value)}
            >
              {availableMacros.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
            </select>
            <ChevronRight size={16} className="absolute right-4 bottom-3 text-blue-500 pointer-events-none rotate-90" />
          </div>
        </div>
      </div>

      {chartProps ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-7 backdrop-blur-2xl shadow-xl shadow-black/40 flex flex-col">
            <div className="flex flex-col xl:flex-row justify-between xl:items-start mb-6 gap-4">
              <div>
                <h3 className="text-lg font-serif font-medium text-slate-200">{selectedTicker} vs {selectedMacro.replace(/_/g, ' ')}</h3>
                <div className="flex flex-col sm:flex-row gap-3 mt-4">
                  <div className="flex bg-[#07050f]/60 border border-[#2d254f]/80 rounded-xl p-1 w-fit shadow-inner">
                    {['30D', '60D', '90D', '180D', '1Y', 'MAX'].map(tf => (
                      <button key={tf} onClick={() => setTimeframe(tf)} className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-200 ${timeframe === tf ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200 hover:bg-[#111c38]'}`}>{tf}</button>
                    ))}
                  </div>
                  {/* The new Lag Feature Control UI */}
                  <div className="flex bg-[#07050f]/60 border border-amber-500/30 rounded-xl p-1 w-fit shadow-inner">
                    {[0, 1, 2, 3, 4, 5, 6].map(m => (
                      <button 
                        key={m} 
                        onClick={() => setLagMonths(m)} 
                        className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-200 ${lagMonths === m ? 'bg-amber-600/80 text-white shadow-md' : 'text-slate-400 hover:text-amber-200 hover:bg-[#111c38]'}`}
                      >
                        {m === 0 ? 'No Lag' : `${m}M Lag`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="flex flex-wrap xl:justify-end items-center gap-6 text-xs font-medium">
                <div className="flex items-center gap-2 text-amber-400"><div className="w-4 h-0.5 bg-amber-500"></div> {selectedTicker} Price</div>
                <div className="flex items-center gap-2 text-blue-400"><div className="w-4 h-0.5 bg-blue-500"></div> Macro Value</div>
              </div>
            </div>

            <div className="relative flex-1 w-full min-h-[350px] mt-2">
              {/* Left Y-Axis (Stock Price) */}
              <div className="absolute left-0 top-0 bottom-6 w-12 flex flex-col justify-between text-[10px] text-amber-500/70 font-medium text-right pr-2 border-r border-[#2d254f]/50 z-10">
                <span>${chartProps.pMax.toFixed(2)}</span>
                <span>${((chartProps.pMax + chartProps.pMin) / 2).toFixed(2)}</span>
                <span>${chartProps.pMin.toFixed(2)}</span>
              </div>
              
              {/* Right Y-Axis (Macro Metric) */}
              <div className="absolute right-0 top-0 bottom-6 w-12 flex flex-col justify-between text-[10px] text-blue-400/70 font-medium text-left pl-2 border-l border-[#2d254f]/50 z-10">
                <span>{chartProps.mMax.toFixed(2)}</span>
                <span>{((chartProps.mMax + chartProps.mMin) / 2).toFixed(2)}</span>
                <span>{chartProps.mMin.toFixed(2)}</span>
              </div>

              {/* Grid Lines */}
              <div className="absolute left-14 right-14 top-0 bottom-6 flex flex-col justify-between pointer-events-none">
                {[...Array(3)].map((_, i) => <div key={i} className="border-t border-[#2d254f]/30 w-full h-0"></div>)}
              </div>
              
              {/* X-Axis Labels */}
              <div className="absolute left-14 right-14 bottom-0 h-6 flex justify-between items-end text-[10px] text-slate-500 font-medium px-1">
                <span>{chartProps.labels[0]}</span>
                <span className="translate-x-1/2 hidden sm:block">{chartProps.labels[1]}</span>
                <span>{chartProps.labels[2]}</span>
              </div>

              {/* SVG Charts */}
              <div className="absolute left-14 right-14 top-0 bottom-6">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible">
                  <path d={chartProps.macroPath} fill="none" stroke="#3b82f6" strokeOpacity="0.8" strokeWidth="2" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                  <path d={chartProps.pricePath} fill="none" stroke="#f59e0b" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
                </svg>
              </div>
            </div>
          </div>

          <div className="space-y-6 flex flex-col">
            <div className={`border rounded-3xl p-6 shadow-xl relative overflow-hidden group transition-colors duration-500 ${
              chartProps.correlation > 0.5 ? 'bg-[#062417]/80 border-emerald-500/30' :
              chartProps.correlation < -0.5 ? 'bg-[#2b101a]/80 border-rose-500/30' :
              'bg-[#111c38]/80 border-[#1e3a8a]/50'
            }`}>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mb-1">Pearson Correlation</p>
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-4xl font-bold tracking-tight transition-colors duration-500 ${
                  chartProps.correlation > 0.5 ? 'text-emerald-400' :
                  chartProps.correlation < -0.5 ? 'text-rose-400' :
                  'text-blue-400'
                }`}>
                  {chartProps.correlation > 0 ? '+' : ''}{chartProps.correlation.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-slate-300">
                {chartProps.correlation > 0.7 ? "Strong Positive: The asset reliably follows this metric." :
                 chartProps.correlation > 0.3 ? "Weak Positive: The asset loosely follows this metric." :
                 chartProps.correlation < -0.7 ? "Strong Negative: The asset reliably inverses this metric." :
                 chartProps.correlation < -0.3 ? "Weak Negative: The asset loosely inverses this metric." :
                 "No significant correlation found in this timeframe."}
              </p>
            </div>

            <div className="bg-[#0d0b1a]/80 border border-amber-500/20 rounded-3xl p-6 shadow-xl">
              <p className="text-[10px] font-bold text-amber-500 uppercase tracking-widest mb-1">{selectedTicker} Timeline Shift</p>
              <div className="flex items-end justify-between mt-2">
                <div>
                  <p className="text-sm text-slate-400">Past</p>
                  <p className="text-lg font-bold text-slate-200">${chartProps.startPrice.toFixed(2)}</p>
                </div>
                <div className="flex pb-1">
                  {chartProps.currPrice > chartProps.startPrice 
                    ? <ArrowUpRight className="text-emerald-400" size={24} /> 
                    : <ArrowDownRight className="text-rose-400" size={24} />}
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-400">Current</p>
                  <p className="text-lg font-bold text-amber-400">${chartProps.currPrice.toFixed(2)}</p>
                </div>
              </div>
            </div>

            <div className="bg-[#0d0b1a]/80 border border-blue-500/20 rounded-3xl p-6 shadow-xl">
              <p className="text-[10px] font-bold text-blue-500 uppercase tracking-widest mb-1">
                Macro Timeline {lagMonths > 0 ? `(Lagged ${lagMonths}M)` : 'Shift'}
              </p>
              <div className="flex items-end justify-between mt-2">
                <div>
                  <p className="text-sm text-slate-400">Past</p>
                  <p className="text-lg font-bold text-slate-200">{chartProps.startMacro.toFixed(2)}</p>
                </div>
                <div className="flex pb-1">
                  {chartProps.currMacro > chartProps.startMacro 
                    ? <ArrowUpRight className="text-blue-400" size={24} /> 
                    : <ArrowDownRight className="text-rose-400" size={24} />}
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-400">Current</p>
                  <p className="text-lg font-bold text-blue-400">{chartProps.currMacro.toFixed(2)}</p>
                </div>
              </div>
            </div>
            
            <button 
              onClick={handleSavePlay}
              disabled={isSaving}
              className={`w-full mt-auto py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all shadow-xl ${saveSuccess ? 'bg-[#062417]/80 text-emerald-400 border border-emerald-500/50' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border border-blue-400/20 shadow-[0_0_20px_rgba(37,99,235,0.3)]'}`}
            >
              {isSaving ? <Loader2 size={18} className="animate-spin" /> : 
               saveSuccess ? <Check size={18} /> : 
               <Star size={18} />}
              {saveSuccess ? 'Saved to AWS' : 'Save Institutional Play'}
            </button>
          </div>
        </div>
      ) : (
        <div className="text-center py-20 text-slate-500">Not enough historical alignment data for this specific pairing.</div>
      )}

      {savedPlays.length > 0 && (
        <div className="pt-8 mt-8 border-t border-[#2d254f]/50 animate-slide-up">
          <div className="flex items-center gap-2 mb-6">
            <Star size={20} className="text-amber-400" />
            <h3 className="text-xl font-serif font-medium text-amber-50/90 tracking-wide">Saved Institutional Plays</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {savedPlays.map((play) => (
              <div 
                key={play.id}
                className={`group bg-[#111c38]/60 border p-5 rounded-2xl cursor-pointer transition-all flex flex-col relative overflow-hidden ${
                  play.correlation > 0.5 ? 'border-emerald-500/30 hover:border-emerald-400/60 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)]' :
                  play.correlation < -0.5 ? 'border-rose-500/30 hover:border-rose-400/60 hover:shadow-[0_0_20px_rgba(244,63,94,0.15)]' :
                  'border-[#1e3a8a]/30 hover:border-blue-500/50 hover:shadow-[0_0_20px_rgba(59,130,246,0.15)]'
                }`}
                onClick={() => {
                  setSelectedTicker(play.ticker);
                  setSelectedMacro(play.macro);
                  if (play.timeframe) setTimeframe(play.timeframe);
                  if (play.lag !== undefined) setLagMonths(play.lag);
                }}
              >
                <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full blur-[20px] pointer-events-none transition-all ${
                  play.correlation > 0.5 ? 'bg-emerald-500/10 group-hover:bg-emerald-500/20' :
                  play.correlation < -0.5 ? 'bg-rose-500/10 group-hover:bg-rose-500/20' :
                  'bg-blue-500/10 group-hover:bg-blue-500/20'
                }`}></div>
                
                <div className="flex justify-between items-start mb-3 relative z-10">
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-slate-200 group-hover:text-white transition-colors">{play.ticker}</span>
                    <span className="text-slate-500 text-xs">×</span>
                  </div>
                  <button 
                    onClick={(e) => { e.stopPropagation(); removePlay(play.id); }}
                    className="text-slate-500 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100 p-1 bg-[#0a1128]/80 rounded-full"
                  >
                    <X size={16} />
                  </button>
                </div>
                
                <div className="text-sm font-medium text-blue-400 truncate w-3/4 mb-4 relative z-10">
                  {play.macro.replace(/_/g, ' ')}
                </div>

                {/* Prominent Correlation Display */}
                <div className="absolute top-4 right-4 text-right">
                  <div className={`text-xl font-bold ${
                    play.correlation > 0.5 ? 'text-emerald-400' :
                    play.correlation < -0.5 ? 'text-rose-400' : 'text-blue-400'
                  }`}>
                    {play.correlation > 0 ? '+' : ''}{(play.correlation || 0).toFixed(2)}
                  </div>
                  <div className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Pearson</div>
                </div>
                
                <div className="mt-auto flex items-center justify-between text-xs relative z-10">
                  <div className="flex gap-2">
                    <span className="font-bold text-slate-300 bg-[#07050f]/60 px-2 py-1 rounded-md border border-[#1e3a8a]/30">
                      {play.timeframe || '180D'} View
                    </span>
                    {/* Render the specific Lag configuration if it exists */}
                    {play.lag > 0 && (
                      <span className="font-bold text-amber-400 bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/30">
                        {play.lag}M Lag
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

// ==========================================
// PORTFOLIO TRACKER COMPONENT
// ==========================================
function PortfolioTracker({ watchList, toggleWatchList, data }) {
  const [benchmark, setBenchmark] = useState('S&P 500');
  const [timeframe, setTimeframe] = useState('30D');

  const portfolioStocks = useMemo(() => {
    return data.filter(s => watchList.includes(s.t));
  }, [data, watchList]);

  const benchmarkStocks = useMemo(() => {
    return data.filter(s => s.idx === benchmark);
  }, [data, benchmark]);

  const stats = useMemo(() => {
    if (portfolioStocks.length === 0) return { avgUpside: 0, currentVal: 0, targetVal: 0 };
    let totalUpside = 0, currentVal = 0, targetVal = 0;
    portfolioStocks.forEach(s => {
      totalUpside += s.upside;
      currentVal += s.close;
      targetVal += s.target;
    });
    return {
      avgUpside: totalUpside / portfolioStocks.length,
      currentVal,
      targetVal
    };
  }, [portfolioStocks]);

  const benchAvgUpside = useMemo(() => {
    if (benchmarkStocks.length === 0) return 0;
    const total = benchmarkStocks.reduce((acc, s) => acc + s.upside, 0);
    return total / benchmarkStocks.length;
  }, [benchmarkStocks]);

  const histReturns = useMemo(() => {
    const getHistReturn = (stocks, days) => {
      if (!stocks || stocks.length === 0) return 0;
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      let total = 0;
      let count = 0;
      
      stocks.forEach(s => {
        if (!s.history || s.history.length === 0) return;
        const currentClose = s.close;
        
        let pastClose = s.history[0].Close_Price; 
        
        for (let i = 0; i < s.history.length; i++) {
          if (new Date(s.history[i].Date) >= cutoff) {
            pastClose = s.history[i].Close_Price || pastClose;
            break;
          }
        }
        
        if (pastClose > 0) {
          total += ((currentClose - pastClose) / pastClose) * 100;
          count++;
        }
      });
      return count > 0 ? total / count : 0;
    };

    return {
      p1M: getHistReturn(portfolioStocks, 30),
      p3M: getHistReturn(portfolioStocks, 90),
      p1Y: getHistReturn(portfolioStocks, 365), 
      b1M: getHistReturn(benchmarkStocks, 30),
      b3M: getHistReturn(benchmarkStocks, 90),
      b1Y: getHistReturn(benchmarkStocks, 365),
    };
  }, [portfolioStocks, benchmarkStocks]);

  const chartSeries = useMemo(() => {
    let days = 30;
    if (timeframe === '60D') days = 60;
    if (timeframe === '90D') days = 90;
    if (timeframe === '180D') days = 180;
    if (timeframe === '1Y') days = 365;
    if (timeframe === 'MAX') days = 1800;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);

    const dateSet = new Set();
    [...portfolioStocks, ...benchmarkStocks].forEach(s => {
      (s.history || []).forEach(r => dateSet.add(r.Date));
    });
    let sortedDates = Array.from(dateSet)
      .sort((a, b) => new Date(a) - new Date(b))
      .filter(d => new Date(d) >= cutoff);

    if (sortedDates.length === 0) sortedDates = [new Date().toISOString().split('T')[0]];
    if (sortedDates.length === 1) {
      const pastDate = new Date(sortedDates[0]);
      pastDate.setDate(pastDate.getDate() - days);
      sortedDates.unshift(pastDate.toISOString().split('T')[0]);
    }

    const historyPoints = sortedDates.map(date => {
      const getAvg = (stocks) => {
        if (!stocks.length) return 100;
        let total = 0;
        stocks.forEach(s => {
          if (s.close === 0) { total += 100; return; }
          const record = (s.history || []).find(r => r.Date === date);
          const closeOnDate = record ? record.Close_Price : s.close;
          total += (closeOnDate / s.close) * 100;
        });
        return total / stocks.length;
      };
      return { x: 0, pVal: getAvg(portfolioStocks), bVal: getAvg(benchmarkStocks), isProj: false };
    });

    historyPoints[historyPoints.length - 1].pVal = 100;
    historyPoints[historyPoints.length - 1].bVal = 100;

    const projCount = 10;
    const projectionPoints = [];
    for (let i = 1; i <= projCount; i++) {
      const progress = i / projCount;
      projectionPoints.push({
        x: 0,
        pVal: 100 + (stats.avgUpside * progress),
        bVal: 100 + (benchAvgUpside * progress),
        isProj: true
      });
    }

    const histWidth = 75;
    const projWidth = 25;
    
    historyPoints.forEach((pt, i) => {
      pt.x = (i / Math.max(1, historyPoints.length - 1)) * histWidth;
    });
    projectionPoints.forEach((pt, i) => {
      pt.x = histWidth + ((i + 1) / projectionPoints.length) * projWidth;
    });

    return [...historyPoints, ...projectionPoints];
  }, [portfolioStocks, benchmarkStocks, timeframe, stats.avgUpside, benchAvgUpside]);

  const minVal = useMemo(() => {
    let min = 95;
    chartSeries.forEach(d => { if (d.pVal < min) min = d.pVal; if (d.bVal < min) min = d.bVal; });
    return min - 5;
  }, [chartSeries]);

  const maxVal = useMemo(() => {
    let max = 105;
    chartSeries.forEach(d => { if (d.pVal > max) max = d.pVal; if (d.bVal > max) max = d.bVal; });
    return max + 5;
  }, [chartSeries]);

  const axisStartLabel = useMemo(() => {
    let days = 30;
    if (timeframe === '60D') days = 60;
    if (timeframe === '90D') days = 90;
    if (timeframe === '180D') days = 180;
    if (timeframe === '1Y') days = 365;
    if (timeframe === 'MAX') days = 1800;
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: timeframe === '1Y' || timeframe === 'MAX' ? '2-digit' : undefined });
  }, [timeframe]);

  const historyData = chartSeries.filter(d => !d.isProj);
  const projectionData = [historyData[historyData.length - 1], ...chartSeries.filter(d => d.isProj)];

  const toPath = (dataset, key) => {
    if (!dataset || dataset.length === 0) return '';
    return dataset.map((d, i) => {
      const y = 100 - ((d[key] - minVal) / (maxVal - minVal)) * 100;
      return `${i === 0 ? 'M' : 'L'} ${d.x} ${y}`;
    }).join(' ');
  };

  if (watchList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-slide-up text-center">
        <div className="w-24 h-24 rounded-full bg-[#111c38]/80 border border-amber-500/30 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(245,158,11,0.2)]">
          <Briefcase size={40} className="text-amber-400" />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">Portfolio is Empty</h2>
        <p className="text-slate-400 max-w-md">Save stocks from the Screener or Target Analysis page to track them permanently here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl animate-slide-up" style={{ animationDuration: '0.3s' }}>
      
      <div className="flex flex-col md:flex-row justify-between md:items-center bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-6 rounded-3xl shadow-xl shadow-black/40 gap-4">
        <div>
          <h2 className="text-2xl font-serif font-medium text-amber-50/90 tracking-wide flex items-center gap-3 drop-shadow-sm">
            <PieChart size={24} className="text-amber-400/80" /> Portfolio Tracker
          </h2>
          <p className="text-sm text-slate-400 mt-1">Permanently tracking {portfolioStocks.length} assets via S3 Cloud Sync.</p>
        </div>
        <div className="relative">
          <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5 ml-1">Compare Against Benchmark</label>
          <select 
            className="w-full md:w-64 bg-[#111c38]/90 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 shadow-inner appearance-none cursor-pointer"
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
          >
            <option value="S&P 500">S&P 500</option>
            <option value="S&P 400">S&P 400 MidCap</option>
            <option value="S&P 600">S&P 600 SmallCap</option>
            <option value="TSX">TSX Composite</option>
          </select>
          <ChevronRight size={16} className="absolute right-4 bottom-3 text-slate-400 pointer-events-none rotate-90" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-3xl bg-[#0d0b1a]/80 border border-[#2d254f]/50 shadow-xl relative overflow-hidden">
           <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">1-Month Outlook (Proj)</h3>
           <div className="text-3xl font-bold text-white mb-2 relative z-10">+{ (stats.avgUpside / 12).toFixed(1) }%</div>
           <p className="text-xs text-blue-400">vs {benchmark}: +{(benchAvgUpside / 12).toFixed(1)}%</p>
        </div>
        <div className="p-6 rounded-3xl bg-[#0d0b1a]/80 border border-[#2d254f]/50 shadow-xl relative overflow-hidden">
           <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">1-Quarter Outlook (Proj)</h3>
           <div className="text-3xl font-bold text-white mb-2 relative z-10">+{ (stats.avgUpside / 4).toFixed(1) }%</div>
           <p className="text-xs text-blue-400">vs {benchmark}: +{(benchAvgUpside / 4).toFixed(1)}%</p>
        </div>
        <div className="p-6 rounded-3xl bg-[#10142b]/80 border border-indigo-500/30 shadow-xl relative overflow-hidden group">
           <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[60px] bg-indigo-500 opacity-30 pointer-events-none"></div>
           <h3 className="text-indigo-300 text-sm font-medium mb-1 relative z-10">1-Year Target Upside</h3>
           <div className="text-3xl font-bold text-white mb-2 relative z-10">+{ stats.avgUpside.toFixed(1) }%</div>
           <p className="text-xs text-indigo-400">vs {benchmark}: +{benchAvgUpside.toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-3xl bg-[#0d0b1a]/80 border border-[#2d254f]/50 shadow-xl relative overflow-hidden">
           <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">Past 1-Month Return</h3>
           <div className={`text-3xl font-bold mb-2 relative z-10 ${histReturns.p1M >= 0 ? 'text-white' : 'text-rose-400'}`}>
             {histReturns.p1M > 0 ? '+' : ''}{histReturns.p1M.toFixed(1)}%
           </div>
           <p className="text-xs text-slate-400">vs {benchmark}: <span className={histReturns.b1M >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{histReturns.b1M > 0 ? '+' : ''}{histReturns.b1M.toFixed(1)}%</span></p>
        </div>
        <div className="p-6 rounded-3xl bg-[#0d0b1a]/80 border border-[#2d254f]/50 shadow-xl relative overflow-hidden">
           <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">Past 1-Quarter Return</h3>
           <div className={`text-3xl font-bold mb-2 relative z-10 ${histReturns.p3M >= 0 ? 'text-white' : 'text-rose-400'}`}>
             {histReturns.p3M > 0 ? '+' : ''}{histReturns.p3M.toFixed(1)}%
           </div>
           <p className="text-xs text-slate-400">vs {benchmark}: <span className={histReturns.b3M >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{histReturns.b3M > 0 ? '+' : ''}{histReturns.b3M.toFixed(1)}%</span></p>
        </div>
        <div className="p-6 rounded-3xl bg-[#0d0b1a]/80 border border-[#2d254f]/50 shadow-xl relative overflow-hidden">
           <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">Past 1-Year Return</h3>
           <div className={`text-3xl font-bold mb-2 relative z-10 ${histReturns.p1Y >= 0 ? 'text-white' : 'text-rose-400'}`}>
             {histReturns.p1Y > 0 ? '+' : ''}{histReturns.p1Y.toFixed(1)}%
           </div>
           <p className="text-xs text-slate-400">vs {benchmark}: <span className={histReturns.b1Y >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{histReturns.b1Y > 0 ? '+' : ''}{histReturns.b1Y.toFixed(1)}%</span></p>
        </div>
      </div>

      <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-7 backdrop-blur-2xl shadow-xl shadow-black/40 flex flex-col">
        <div className="flex flex-col xl:flex-row justify-between xl:items-start mb-6 gap-4">
          <div>
            <h3 className="text-lg font-serif font-medium text-amber-50/90">Historical & Projected Trajectory</h3>
            <p className="text-xs text-slate-400 mt-1">Relative performance tracking and 1-Year mean target forecasts</p>
            <div className="flex bg-[#07050f]/60 border border-[#2d254f]/80 rounded-xl p-1 mt-4 w-fit shadow-inner">
              {['30D', '60D', '90D', '180D', '1Y', 'MAX'].map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-200 ${
                    timeframe === tf 
                      ? 'bg-blue-600 text-white shadow-md' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#111c38]'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs font-medium mt-2 xl:mt-0">
            <div className="flex items-center gap-1.5 text-amber-400">
              <div className="w-3 h-0.5 bg-amber-500"></div> My Portfolio
            </div>
            <div className="flex items-center gap-1.5 text-slate-500">
              <div className="w-3 h-0.5 border-t border-dashed border-slate-500"></div> {benchmark}
            </div>
          </div>
        </div>

        <div className="relative w-full h-[280px]">
           <div className="absolute left-0 top-0 bottom-6 w-12 flex flex-col justify-between text-[10px] text-slate-500 font-medium text-right pr-3 border-r border-[#2d254f]/50">
             <span>{maxVal.toFixed(0)}</span>
             <span>{((maxVal + minVal) / 2).toFixed(0)}</span>
             <span>{minVal.toFixed(0)}</span>
           </div>
           
           <div className="absolute top-0 bottom-6 w-px bg-blue-500/20 z-0 pointer-events-none" style={{ left: 'calc(3rem + 75%)' }}></div>

           <div className="absolute left-14 right-0 top-0 bottom-6 flex flex-col justify-between pointer-events-none">
             {[...Array(3)].map((_, i) => (
               <div key={i} className="border-t border-[#2d254f]/30 w-full h-0"></div>
             ))}
           </div>
           
           <div className="absolute left-14 right-0 bottom-0 h-6 text-[10px] text-slate-500 font-medium">
             <span className="absolute left-0 bottom-0">{axisStartLabel}</span>
             <span className="absolute bottom-0 text-blue-400" style={{ left: '75%', transform: 'translateX(-50%)' }}>Today</span>
             <span className="absolute right-0 bottom-0">1 Year Target</span>
           </div>

           <div className="absolute left-14 right-0 top-0 bottom-6">
             <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible">
                <path d={toPath(historyData, 'bVal')} fill="none" stroke="#64748b" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                <path d={toPath(projectionData, 'bVal')} fill="none" stroke="#64748b" strokeOpacity="0.4" strokeWidth="1" strokeDasharray="2 4" vectorEffect="non-scaling-stroke" />
                
                <path d={toPath(historyData, 'pVal')} fill="none" stroke="#f59e0b" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
                <path d={toPath(projectionData, 'pVal')} fill="none" stroke="#f59e0b" strokeOpacity="0.6" strokeWidth="2" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
                
                <circle cx="75" cy={100 - ((100 - minVal) / (maxVal - minVal)) * 100} r="1.5" fill="#f59e0b" className="animate-pulse" />
             </svg>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {portfolioStocks.map(stock => (
          <div key={stock.t} className="bg-[#111c38]/60 border border-[#1e3a8a]/30 p-4 rounded-2xl flex items-center justify-between group hover:border-[#1e3a8a]/80 transition-colors shadow-lg">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-bold text-white text-lg">{stock.t}</span>
                <span className="text-[9px] uppercase tracking-wider bg-[#07050f]/60 px-1.5 py-0.5 rounded text-slate-400 border border-[#1e3a8a]/30">{stock.idx}</span>
              </div>
              <div className="text-xs text-slate-400 mb-2 truncate w-40">{stock.n}</div>
              <div className="flex gap-4">
                <div>
                  <div className="text-[9px] text-slate-500 uppercase">Close</div>
                  <div className="font-medium text-slate-300">${stock.close.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[9px] text-slate-500 uppercase">Target</div>
                  <div className={`font-medium ${stock.upside > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    ${stock.target.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
            <button 
              onClick={() => toggleWatchList(stock.t)}
              className="w-8 h-8 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-rose-500 hover:text-white transition-all"
              title="Remove from Portfolio"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// EXISTING COMPONENTS (HOME, SCREENER, NEWS, ETC)
// ==========================================

function DashboardHome({ totalStocks, data = [], sentiment, savedStocks = [], toggleSaved }) {
  const assetBreakdown = useMemo(() => {
    if (!data || data.length === 0) return null;
    const counts = {};
    data.forEach(stock => {
      const idx = stock.idx || 'Other';
      counts[idx] = (counts[idx] || 0) + 1;
    });
    return Object.entries(counts).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count);
  }, [data]);

  const anomalies = useMemo(() => {
    if (!data || data.length === 0) return [];
    const flagged = data.map(stock => {
      const rec = stock.latestRecord || {};
      let flagReason = null;
      if (rec.Volume && rec.Average_Volume && rec.Volume > (rec.Average_Volume * 3)) flagReason = "Massive Volume Spike";
      else if (stock.peRatio > 1 && stock.peRatio < 8) flagReason = `Deep Value (P/E: ${stock.peRatio.toFixed(1)})`;
      else if (stock.upside > 50) flagReason = `Extreme Target (+${stock.upside.toFixed(0)}%)`;
      if (flagReason) return { ...stock, flagReason };
      return null;
    }).filter(Boolean);
    return flagged.sort((a, b) => b.upside - a.upside);
  }, [data]);

  const latestSentiment = sentiment[sentiment.length - 1] || { sentiment: 'Neutral', confidence: 0, summary: '...' };
  const isBullish = latestSentiment.sentiment === 'Bullish';
  const isNeutral = latestSentiment.sentiment === 'Neutral';

  const sentimentSparkline = useMemo(() => {
    const getScore = (s) => {
        if (!s || !s.confidence || s.confidence === '--') return 50;
        if (s.sentiment === 'Bullish') return 50 + (s.confidence / 2);
        if (s.sentiment === 'Bearish') return 50 - (s.confidence / 2);
        return 50;
    };
    let scores = sentiment.map(getScore);
    
    if (scores.length > 0 && scores.length < 7) {
        const latestScore = scores[scores.length - 1];
        const mockScores = [];
        let current = 50; 
        for (let i = 0; i < 7 - scores.length; i++) {
            mockScores.push(current);
            current = current + (latestScore - current) * 0.3 + (Math.random() * 8 - 4);
        }
        scores = [...mockScores, ...scores];
    } else if (scores.length === 0) {
        scores = [50, 50, 50, 50, 50, 50, 50];
    }
    return scores;
  }, [sentiment]);

  const [trendFilter, setTrendFilter] = useState('All');
  const [timeframe, setTimeframe] = useState('30D');

  const trendData = useMemo(() => {
    const barCount = 30; 
    let baseData = [];
    for (let i = 0; i < barCount; i++) {
      let val = 50;
      const normalized = i / barCount;
      if (timeframe === '30D') val = 40 + 35 * Math.sin(normalized * Math.PI * 2) + 15 * Math.cos(normalized * Math.PI * 4);
      else if (timeframe === '60D') val = 45 + 25 * Math.sin(normalized * Math.PI * 2.5) + 20 * Math.cos(normalized * Math.PI * 1.5);
      else if (timeframe === '90D') val = 55 + 30 * Math.cos(normalized * Math.PI * 3) - 10 * Math.sin(normalized * Math.PI * 2);
      else if (timeframe === '180D') val = 60 + 20 * Math.sin(normalized * Math.PI * 1.5) + 25 * Math.cos(normalized * Math.PI * 5);
      else if (timeframe === '1Y') val = 65 - 25 * Math.cos(normalized * Math.PI * 2) + 15 * Math.sin(normalized * Math.PI * 4);
      else val = 70 + 20 * Math.sin(normalized * Math.PI * 6) - 15 * Math.cos(normalized * Math.PI * 3);
      baseData.push(Math.max(15, Math.min(100, val + (Math.random() * 10 - 5)))); 
    }
    const applyTheme = (v, scale, cFrom, cTo, hFrom, hTo, bColor) => ({
      height: Math.min(v * scale, 100), colorFrom: cFrom, colorTo: cTo, hoverFrom: hFrom, hoverTo: hTo, border: bColor
    });
    if (trendFilter === 'S&P 500') return baseData.map(v => applyTheme(v, 1.2, 'from-blue-900/40', 'to-blue-400/30', 'hover:from-blue-600/50', 'hover:to-blue-300/50', 'border-blue-400/40'));
    if (trendFilter === 'S&P 400') return baseData.map(v => applyTheme(v, 0.85, 'from-emerald-900/40', 'to-emerald-400/30', 'hover:from-emerald-600/50', 'hover:to-emerald-300/50', 'border-emerald-400/40'));
    if (trendFilter === 'S&P 600') return baseData.map(v => applyTheme(v, 0.7, 'from-amber-900/40', 'to-amber-400/30', 'hover:from-amber-600/50', 'hover:to-amber-300/50', 'border-amber-400/40'));
    if (trendFilter === 'TSX') return baseData.map(v => applyTheme(v, 0.6, 'from-rose-900/40', 'to-rose-400/30', 'hover:from-rose-600/50', 'hover:to-rose-300/50', 'border-rose-400/40'));
    return baseData.map(v => applyTheme(v, 1.0, 'from-purple-900/40', 'to-indigo-400/30', 'hover:from-purple-600/50', 'hover:to-indigo-300/50', 'border-indigo-400/40'));
  }, [trendFilter, timeframe]);

  const axisLabels = useMemo(() => {
    const today = new Date();
    const start = new Date();
    let days = 30;
    if (timeframe === '60D') days = 60;
    if (timeframe === '90D') days = 90;
    if (timeframe === '180D') days = 180;
    if (timeframe === '1Y') days = 360;
    if (timeframe === 'MAX') days = 1800; 
    start.setDate(today.getDate() - days);
    const mid = new Date(start.getTime() + (today.getTime() - start.getTime()) / 2);
    const formatDt = (d) => {
      const opts = { month: 'short', day: 'numeric' };
      if (timeframe === '1Y' || timeframe === 'MAX') opts.year = '2-digit';
      return d.toLocaleDateString('en-US', opts);
    };
    return [formatDt(start), formatDt(mid), 'Today'];
  }, [timeframe]);

  return (
    <div className="space-y-6 max-w-7xl animate-slide-up" style={{ animationDuration: '0.3s' }}>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard title="Total Assets Tracked" value={totalStocks > 0 ? totalStocks.toLocaleString() : "..."} breakdown={assetBreakdown} />
        <MetricCard 
          title="AI Market Sentiment" 
          value={latestSentiment.sentiment} 
          subtitle={latestSentiment.summary} 
          trend={`Confidence: ${latestSentiment.confidence}%`} 
          alert={!isBullish && !isNeutral} 
          highlight={isBullish}
          sparkline={sentimentSparkline}
          sparklineColor={isBullish ? '#34d399' : isNeutral ? '#94a3b8' : '#fb7185'} 
        />
        <MetricCard title="Anomalies Detected" value={data.length > 0 ? anomalies.length.toString() : "..."} subtitle="Deviating from Industry" trend="Action Required" highlight />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-7 backdrop-blur-2xl shadow-xl shadow-black/40 relative overflow-hidden group flex flex-col">
          <div className="flex flex-col xl:flex-row justify-between xl:items-start mb-6 relative z-10 gap-4">
            <div>
              <h2 className="text-xl font-serif font-medium text-amber-50/90 tracking-wide drop-shadow-sm">Market Volume Trends</h2>
              <div className="flex bg-[#07050f]/60 border border-[#2d254f]/80 rounded-xl p-1 mt-3 w-fit shadow-inner">
                {['30D', '60D', '90D', '180D', '1Y', 'MAX'].map(tf => (
                  <button key={tf} onClick={() => setTimeframe(tf)} className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-200 ${timeframe === tf ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200 hover:bg-[#111c38]'}`}>{tf}</button>
                ))}
              </div>
            </div>
            <select className="bg-[#07050f]/80 border border-[#2d254f]/80 rounded-xl px-4 py-2 text-sm focus:outline-none text-slate-300 backdrop-blur-md cursor-pointer shadow-inner" value={trendFilter} onChange={(e) => setTrendFilter(e.target.value)}>
              <option value="All">All Markets</option>
              <option value="S&P 500">S&P 500</option>
              <option value="S&P 400">S&P 400 MidCap</option>
              <option value="S&P 600">S&P 600 SmallCap</option>
              <option value="TSX">TSX Composite</option>
            </select>
          </div>
          
          <div className="relative flex-1 w-full mt-2 flex pb-6 pl-12 min-h-[220px]">
            <div className="absolute left-0 top-0 bottom-6 w-10 flex flex-col justify-between text-[10px] text-slate-500 font-medium text-right pr-3 border-r border-[#2d254f]/50">
              <span>100M</span><span>75M</span><span>50M</span><span>25M</span><span>0M</span>
            </div>
            <div className="absolute left-12 right-0 top-0 bottom-6 flex flex-col justify-between pointer-events-none">
              {[...Array(5)].map((_, i) => <div key={i} className="border-t border-[#2d254f]/30 w-full h-0"></div>)}
            </div>
            <div className="absolute left-12 right-0 bottom-0 h-6 flex justify-between items-end text-[10px] text-slate-500 font-medium px-1">
              <span>{axisLabels[0]}</span><span className="translate-x-1/2 hidden sm:block">{axisLabels[1]}</span><span>{axisLabels[2]}</span>
            </div>
            <div className="h-full w-full flex items-end space-x-1 sm:space-x-2 relative z-10 pt-4">
              {trendData.map((item, i) => (
                <div key={i} className={`flex-1 bg-gradient-to-t ${item.colorFrom} ${item.colorTo} rounded-t-md border-t ${item.border} ${item.hoverFrom} ${item.hoverTo} transition-all duration-300 cursor-pointer relative group`} style={{ height: `${item.height}%` }}></div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-7 backdrop-blur-2xl shadow-xl shadow-black/40 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-serif font-medium text-amber-50/90 tracking-wide drop-shadow-sm">Anomaly Alerts</h2>
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          </div>
          <div className="space-y-3 flex-1 overflow-y-auto max-h-[300px] pr-2 custom-scrollbar">
            {anomalies.length > 0 ? anomalies.slice(0, 6).map((stock, idx) => (
              <div key={idx} className="flex items-center justify-between p-3.5 rounded-2xl bg-[#16122b]/60 hover:bg-[#201a3d]/80 transition-all duration-300 cursor-pointer border border-transparent hover:border-purple-500/20 group">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-200 group-hover:text-purple-300 transition-colors">{stock.t}</span>
                    <span className="text-[9px] uppercase tracking-wider bg-[#07050f]/60 border border-[#2d254f]/50 px-1.5 py-0.5 rounded text-slate-400">{stock.sec.substring(0, 10)}</span>
                  </div>
                  <p className="text-xs text-indigo-400 font-medium mt-0.5">{stock.flagReason}</p>
                </div>
                <div className="text-right mr-4">
                  <p className="font-medium text-slate-200">${(stock.close || 0).toFixed(2)}</p>
                  <p className={`text-xs flex items-center justify-end font-medium mt-0.5 ${stock.upside > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {stock.upside > 0 ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
                    {stock.upside.toFixed(1)}%
                  </p>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); toggleSaved(stock.t); }}
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all ${savedStocks.includes(stock.t) ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_12px_rgba(37,99,235,0.5)]' : 'bg-[#111c38] hover:bg-[#1e3a8a] text-slate-400 hover:text-white border border-[#1e3a8a]/50'}`}
                >
                  {savedStocks.includes(stock.t) ? <Check size={14} /> : <Plus size={14} />}
                </button>
              </div>
            )) : <div className="flex items-center justify-center h-full text-slate-500 text-sm">No extreme anomalies detected today.</div>}
          </div>
          <button className="w-full mt-4 py-3 text-sm text-purple-400 hover:text-purple-300 bg-purple-500/5 hover:bg-purple-500/10 rounded-xl font-medium flex items-center justify-center transition-colors border border-purple-500/10">
            View All {anomalies.length} Anomalies <ChevronRight size={16} className="ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MacroScreener({ data, savedStocks, toggleSaved }) {
  const [filterIndex, setFilterIndex] = useState('All');
  const [minUpside, setMinUpside] = useState(10);
  const [sortOrder, setSortOrder] = useState('upside-desc');
  const [filterSector, setFilterSector] = useState('All');

  const availableSectors = useMemo(() => {
    const sectors = new Set(data.map(d => d.sec));
    return ['All', ...Array.from(sectors).sort()];
  }, [data]);

  const filteredData = useMemo(() => {
    let result = data.filter(s => {
      const matchIndex = filterIndex === 'All' || s.idx === filterIndex;
      const matchSector = filterSector === 'All' || s.sec === filterSector;
      const matchUpside = s.upside >= minUpside;
      return matchIndex && matchSector && matchUpside;
    });
    if (sortOrder === 'upside-desc') result.sort((a, b) => b.upside - a.upside);
    else if (sortOrder === 'upside-asc') result.sort((a, b) => a.upside - b.upside);
    else if (sortOrder === 'ticker-asc') result.sort((a, b) => a.t.localeCompare(b.t));
    return result;
  }, [data, filterIndex, filterSector, minUpside, sortOrder]);

  return (
    <div className="space-y-6 animate-slide-up" style={{ animationDuration: '0.3s' }}>
      <div className="bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-6 rounded-3xl shadow-xl shadow-black/40">
        <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-serif font-medium text-amber-50/90 tracking-wide flex items-center gap-3 drop-shadow-sm">
              <Filter size={24} className="text-amber-400/80" /> Global Macro Screener
            </h2>
            <p className="text-sm text-slate-400 mt-1">Scanning {data.length} assets synced live from AWS S3.</p>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500 mb-1">Found Opportunities</div>
            <div className="text-2xl font-bold text-emerald-400">{filteredData.length} <span className="text-sm font-normal text-slate-400">matching criteria</span></div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 p-4 bg-[#07050f]/60 rounded-2xl border border-[#1e3a8a]/30">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Market / Index</label>
            <select className="w-full bg-[#111c38]/80 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500" value={filterIndex} onChange={(e) => setFilterIndex(e.target.value)}>
              <option value="All">All Markets</option><option value="TSX">TSX Composite</option><option value="S&P 500">S&P 500</option><option value="S&P 400">S&P 400 MidCap</option><option value="S&P 600">S&P 600 SmallCap</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Target Opportunity</label>
            <select className="w-full bg-[#111c38]/80 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500" value={minUpside} onChange={(e) => setMinUpside(Number(e.target.value))}>
              <option value={0}>Show All (&gt; 0%)</option><option value={10}>Aggressive (&gt; 10%)</option><option value={15}>High Conviction (&gt; 15%)</option><option value={25}>Deep Value (&gt; 25%)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Sort By</label>
            <select className="w-full bg-[#111c38]/80 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
              <option value="upside-desc">Upside (Highest First)</option><option value="upside-asc">Upside (Lowest First)</option><option value="ticker-asc">Ticker (A-Z)</option>
            </select>
          </div>
          <div>
             <label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Sector</label>
             <select className="w-full bg-[#111c38]/80 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500" value={filterSector} onChange={(e) => setFilterSector(e.target.value)}>
               {availableSectors.map(sec => <option key={sec} value={sec}>{sec}</option>)}
             </select>
          </div>
          <div className="flex items-end">
            <button className="w-full bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 py-2.5 rounded-xl font-medium transition-colors text-sm flex items-center justify-center gap-2">
              <RefreshCw size={14} /> Refresh S3
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredData.slice(0, 50).map((stock) => (
          <StockScreenerCard key={stock.t} stock={stock} isSaved={savedStocks.includes(stock.t)} onToggle={() => toggleSaved(stock.t)} />
        ))}
      </div>
    </div>
  );
}

function StockScreenerCard({ stock, isSaved, onToggle }) {
  const hasHistory = stock.histClose && stock.histClose.length > 1;
  const allPrices = hasHistory ? [...stock.histClose, ...stock.histTarget] : [stock.close, stock.target];
  const minVal = Math.min(...allPrices) * 0.95;
  const maxVal = Math.max(...allPrices) * 1.05;

  const toPath = (data) => {
    if (!data || data.length === 0) return '';
    if (data.length === 1) return `M 0 50 L 100 50`;
    return data.map((v, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((v - minVal) / (maxVal - minVal)) * 100;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  return (
    <div className="bg-[#080c17]/80 border border-[#1e3a8a]/20 rounded-2xl p-5 hover:border-[#1e3a8a]/40 transition-all duration-300 relative group shadow-lg shadow-black/20">
       <div className="flex justify-between items-start mb-4">
         <div>
           <div className="flex items-center gap-2 mb-1 flex-wrap">
             <h3 className="text-xl font-bold text-slate-200 group-hover:text-white transition-colors">{stock.t}</h3>
             <span className="text-[9px] font-bold tracking-wider uppercase bg-[#111c38] text-slate-400 px-2 py-0.5 rounded border border-[#1e3a8a]/30 whitespace-nowrap">{stock.idx}</span>
             <span className="text-[9px] font-bold tracking-wider uppercase bg-[#111c38] text-slate-400 px-2 py-0.5 rounded border border-[#1e3a8a]/30 whitespace-nowrap overflow-hidden text-ellipsis max-w-[120px]">{stock.sec}</span>
           </div>
           <p className="text-sm text-slate-500 truncate w-48">{stock.n}</p>
         </div>
         <button onClick={onToggle} className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all ${isSaved ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_12px_rgba(37,99,235,0.5)]' : 'bg-[#111c38] hover:bg-[#1e3a8a] text-slate-400 hover:text-white border border-[#1e3a8a]/50'}`}>
           {isSaved ? <Check size={16} /> : <Plus size={16} />}
         </button>
       </div>
       <div className="grid grid-cols-2 gap-4 mb-3">
         <div>
           <p className="text-[11px] font-medium text-slate-500 mb-0.5">Close Price</p>
           <p className="text-lg font-bold text-slate-200">${(stock.close || 0).toFixed(2)}</p>
         </div>
         <div>
           <p className="text-[11px] font-medium text-slate-500 mb-0.5">Analyst Target</p>
           <div className="flex items-center gap-2">
             <p className="text-lg font-bold text-emerald-400">${(stock.target || 0).toFixed(2)}</p>
             <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">+{stock.upside.toFixed(1)}%</span>
           </div>
         </div>
       </div>
       <div className="h-16 w-full relative mt-4 opacity-80 group-hover:opacity-100 transition-opacity">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible">
            <defs>
              <linearGradient id={`grad-${stock.t.replace('.','')}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" /><stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
              </linearGradient>
            </defs>
            {hasHistory ? (
              <>
                <path d={toPath(stock.histTarget)} fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />
                <path d={`${toPath(stock.histClose)} L 100 100 L 0 100 Z`} fill={`url(#grad-${stock.t.replace('.','')})`} />
                <path d={toPath(stock.histClose)} fill="none" stroke="#3b82f6" strokeWidth="2" vectorEffect="non-scaling-stroke" />
              </>
            ) : <text x="50" y="50" fill="#64748b" fontSize="10" textAnchor="middle" alignmentBaseline="middle">Gathering History (Day 1)...</text>}
          </svg>
       </div>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }) {
  const [ripples, setRipples] = useState([]);
  const handleRippleClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const newRipple = { x: e.clientX - rect.left, y: e.clientY - rect.top, id: Date.now() };
    setRipples(prev => [...prev, newRipple]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== newRipple.id)), 1200);
    if (onClick) onClick(e);
  };
  return (
    <button onClick={handleRippleClick} className={`relative overflow-hidden w-full flex items-center space-x-3 px-4 py-3 rounded-2xl transition-all duration-300 group ${active ? 'bg-gradient-to-r from-blue-600/20 to-indigo-600/10 text-blue-300 border border-blue-500/30 shadow-[inset_0_0_20px_rgba(59,130,246,0.05)]' : 'text-slate-400 hover:bg-[#111c38]/80 hover:text-slate-200 border border-transparent'}`}>
      {ripples.map(r => <span key={r.id} className="absolute rounded-full pointer-events-none" style={{ left: r.x, top: r.y, width: '100px', height: '100px', background: 'radial-gradient(circle, rgba(59,130,246,0.8) 0%, rgba(99,102,241,0.4) 40%, rgba(0,0,0,0) 80%)', transform: 'translate(-50%, -50%) scale(0)', animation: 'nav-ripple 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards' }} />)}
      <span className={`relative z-10 ${active ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300 transition-colors'}`}>{icon}</span>
      <span className="relative z-10 font-medium text-sm tracking-wide">{label}</span>
    </button>
  );
}

function MetricCard({ title, value, subtitle, trend, highlight, alert, breakdown, sparkline, sparklineColor }) {
  const toPath = (data) => {
    if (!data || data.length === 0) return '';
    const min = 0; const max = 100;
    return data.map((v, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 100 - ((v - min) / (max - min)) * 100;
        return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  return (
    <div className={`p-6 rounded-3xl border backdrop-blur-2xl relative overflow-hidden transition-all duration-300 hover:-translate-y-1 shadow-xl shadow-black/40 ${highlight ? 'bg-[#10142b]/80 border-indigo-500/30 hover:shadow-[0_8px_30px_rgba(99,102,241,0.15)]' : alert ? 'bg-[#2b101a]/80 border-rose-500/30 hover:shadow-[0_8px_30px_rgba(244,63,94,0.15)]' : 'bg-[#0d0b1a]/80 border-[#2d254f]/50 hover:border-[#3e356e]/50'}`}>
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[60px] pointer-events-none opacity-30 ${highlight ? 'bg-indigo-500' : alert ? 'bg-rose-500' : 'bg-purple-500'}`}></div>
      
      {sparkline && (
        <div className="absolute bottom-0 left-0 right-0 h-[70%] opacity-40 pointer-events-none z-0">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible">
            <path d={toPath(sparkline)} fill="none" stroke={sparklineColor} strokeWidth="3" vectorEffect="non-scaling-stroke" />
            <path d={`${toPath(sparkline)} L 100 100 L 0 100 Z`} fill={sparklineColor} opacity="0.15" />
          </svg>
        </div>
      )}

      <h3 className="text-slate-400 text-sm font-medium mb-1 relative z-10">{title}</h3>
      <div className="text-4xl font-bold text-white mb-2 tracking-tight relative z-10">{value}</div>
      {breakdown && breakdown.length > 0 ? (
        <div className="mt-4 grid grid-cols-2 gap-2 relative z-10">
          {breakdown.map((item, i) => (
            <div key={i} className="flex justify-between items-center bg-[#111c38]/60 border border-[#1e3a8a]/30 px-2.5 py-1.5 rounded-lg shadow-inner">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider truncate mr-1">{item.label}</span><span className="text-xs font-bold text-blue-400">{item.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center justify-between mt-5 relative z-10">
          <span className="text-xs text-slate-400">{subtitle}</span>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg border backdrop-blur-md ${highlight ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30' : alert ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'}`}>{trend}</span>
        </div>
      )}
    </div>
  );
}

function TargetAnalysis({ savedStocks, watchList, toggleWatchList, data }) {
  const [selectedTicker, setSelectedTicker] = useState('');
  const [timeframe, setTimeframe] = useState('30D');

  const combinedAssets = useMemo(() => [...new Set([...savedStocks, ...watchList])], [savedStocks, watchList]);

  useEffect(() => {
    if (combinedAssets.length > 0 && (!selectedTicker || !combinedAssets.includes(selectedTicker))) {
      setSelectedTicker(combinedAssets[0]);
    }
  }, [combinedAssets, selectedTicker]);

  const stock = data.find(s => s.t === selectedTicker);
  const history = stock ? (stock.history || []) : [];
  const hasHistory = history.length > 1;

  const filteredHistory = useMemo(() => {
    if (!hasHistory) return history;
    if (timeframe === 'MAX') return history;
    let days = 30;
    if (timeframe === '60D') days = 60;
    if (timeframe === '90D') days = 90;
    if (timeframe === '180D') days = 180;
    if (timeframe === '1Y') days = 365;
    const latestDateStr = history[history.length - 1].Date;
    const latestDate = new Date(latestDateStr);
    const cutoffDate = new Date(latestDate);
    cutoffDate.setDate(latestDate.getDate() - days);
    return history.filter(record => new Date(record.Date) >= cutoffDate);
  }, [history, timeframe, hasHistory]);

  const displayHistory = filteredHistory.length > 1 ? filteredHistory : history;

  const axisLabels = useMemo(() => {
    if (!hasHistory || displayHistory.length === 0) return ['', '', 'Today'];
    const start = new Date(displayHistory[0].Date);
    const end = new Date(displayHistory[displayHistory.length - 1].Date);
    const mid = new Date(start.getTime() + (end.getTime() - start.getTime()) / 2);
    const formatDt = (d) => {
      const opts = { month: 'short', day: 'numeric' };
      if (timeframe === '1Y' || timeframe === 'MAX') opts.year = '2-digit';
      return d.toLocaleDateString('en-US', opts);
    };
    return [formatDt(start), formatDt(mid), formatDt(end)];
  }, [displayHistory, timeframe, hasHistory]);

  if (!combinedAssets || combinedAssets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-slide-up text-center">
        <div className="w-24 h-24 rounded-full bg-[#111c38]/80 border border-[#1e3a8a]/50 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(30,58,138,0.3)]">
          <LineChart size={40} className="text-blue-500/50" />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">Analysis Queue Empty</h2>
        <p className="text-slate-400 max-w-md">Add assets from the Macro Screener to your Pipeline, or select from your saved Portfolio.</p>
      </div>
    );
  }

  if (!stock) return null;

  const prices = hasHistory ? displayHistory.map(r => r.Close_Price) : [stock.close, stock.close];
  const targets = hasHistory ? displayHistory.map(r => r.Target_Mean_Price || r.Close_Price) : [stock.target, stock.target];

  const peakPrice = Math.max(...prices);
  let deepestDiscount = 0;
  let minRatio = 1;
  let maxRatio = 1;
  
  if (hasHistory) {
    const ratios = [];
    prices.forEach((p, i) => {
       const t = targets[i];
       const upside = t > 0 ? ((t - p) / p) * 100 : 0;
       if (upside > deepestDiscount) deepestDiscount = upside;
       ratios.push(t > 0 ? p / t : 1); 
    });
    minRatio = Math.min(...ratios);
    maxRatio = Math.max(...ratios);
  } else {
    deepestDiscount = stock.upside;
    minRatio = stock.target > 0 ? stock.close / stock.target : 1;
    maxRatio = minRatio;
  }

  const lowestBoundData = targets.map(t => t * minRatio);
  const highestBoundData = targets.map(t => t * maxRatio);

  const allChartValues = [...prices, ...targets, ...lowestBoundData, ...highestBoundData];
  const minVal = Math.min(...allChartValues) * 0.90; 
  const maxVal = Math.max(...allChartValues) * 1.10;

  const toPath = (dataset) => {
    if (!dataset || dataset.length === 0) return '';
    return dataset.map((v, i) => {
      const x = (i / (dataset.length - 1)) * 100;
      const y = 100 - ((v - minVal) / (maxVal - minVal)) * 100;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  return (
    <div className="max-w-6xl space-y-6 animate-slide-up" style={{ animationDuration: '0.3s' }}>
      <div className="flex flex-col md:flex-row justify-between md:items-center bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-6 rounded-3xl shadow-xl shadow-black/40 gap-4">
        <div>
           <div className="flex items-center gap-3 mb-1">
             <h2 className="text-3xl font-bold text-white tracking-tight">{stock.t}</h2>
             <button 
               onClick={() => toggleWatchList(stock.t)}
               className={`p-1.5 rounded-lg transition-all border ${watchList.includes(stock.t) ? 'bg-amber-500/20 border-amber-500/50 text-amber-400' : 'bg-[#111c38] border-[#1e3a8a]/50 text-slate-500 hover:text-amber-400 hover:border-amber-500/50'}`}
               title={watchList.includes(stock.t) ? "Remove from Portfolio" : "Add to Portfolio"}
             >
               <Star size={20} fill={watchList.includes(stock.t) ? 'currentColor' : 'none'} />
             </button>
             <span className="text-[10px] font-bold tracking-widest uppercase bg-blue-500/20 text-blue-300 px-2 py-1 rounded-md border border-blue-500/30">{stock.idx}</span>
             <span className="text-[10px] font-bold tracking-widest uppercase bg-purple-500/20 text-purple-300 px-2 py-1 rounded-md border border-purple-500/30">{stock.sec}</span>
           </div>
           <p className="text-slate-400 font-medium">{stock.n}</p>
        </div>

        <div className="relative">
          <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5 ml-1">Select Asset to Analyze</label>
          <select 
            className="w-full md:w-64 bg-[#111c38]/90 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 shadow-inner appearance-none cursor-pointer"
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
          >
            {savedStocks.length > 0 && <optgroup label="Active Pipeline">
              {savedStocks.map(t => <option key={`pipe-${t}`} value={t}>{t}</option>)}
            </optgroup>}
            {watchList.length > 0 && <optgroup label="Saved Portfolio">
              {watchList.map(t => <option key={`watch-${t}`} value={t}>{t}</option>)}
            </optgroup>}
          </select>
          <ChevronRight size={16} className="absolute right-4 bottom-3 text-slate-400 pointer-events-none rotate-90" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-7 backdrop-blur-2xl shadow-xl shadow-black/40 flex flex-col">
          <div className="flex flex-col xl:flex-row justify-between xl:items-start mb-6 gap-4">
            <div>
              <h3 className="text-lg font-serif font-medium text-amber-50/90">Time Series Overlay</h3>
              <p className="text-xs text-slate-400 mt-1">Comparing Closing Price vs. Analyst Mean Target</p>
              <div className="flex bg-[#07050f]/60 border border-[#2d254f]/80 rounded-xl p-1 mt-4 w-fit shadow-inner">
                {['30D', '60D', '90D', '180D', '1Y', 'MAX'].map(tf => (
                  <button key={tf} onClick={() => setTimeframe(tf)} className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-200 ${timeframe === tf ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200 hover:bg-[#111c38]'}`}>{tf}</button>
                ))}
              </div>
            </div>
            
            <div className="flex flex-wrap xl:justify-end items-center gap-4 text-xs font-medium">
              <div className="flex items-center gap-1.5 text-amber-500/80"><div className="w-3 h-0.5 border-t border-dashed border-amber-500/80"></div> Peak Rel.</div>
              <div className="flex items-center gap-1.5 text-blue-400"><div className="w-3 h-0.5 bg-blue-500"></div> Close</div>
              <div className="flex items-center gap-1.5 text-emerald-400"><div className="w-3 h-0.5 border-t border-dashed border-emerald-500"></div> Target</div>
              <div className="flex items-center gap-1.5 text-rose-500/80"><div className="w-3 h-0.5 border-t border-dashed border-rose-500/80"></div> Floor Rel.</div>
            </div>
          </div>

          <div className="relative flex-1 w-full min-h-[300px] mt-2">
            <div className="absolute left-0 top-0 bottom-6 w-12 flex flex-col justify-between text-[10px] text-slate-500 font-medium text-right pr-3 border-r border-[#2d254f]/50">
              <span>${maxVal.toFixed(0)}</span><span>${((maxVal + minVal) / 2).toFixed(0)}</span><span>${minVal.toFixed(0)}</span>
            </div>
            <div className="absolute left-14 right-0 top-0 bottom-6 flex flex-col justify-between pointer-events-none">
              {[...Array(3)].map((_, i) => <div key={i} className="border-t border-[#2d254f]/30 w-full h-0"></div>)}
            </div>
            <div className="absolute left-14 right-0 bottom-0 h-6 flex justify-between items-end text-[10px] text-slate-500 font-medium px-1">
              <span>{axisLabels[0]}</span><span className="translate-x-1/2 hidden sm:block">{axisLabels[1]}</span><span>{axisLabels[2]}</span>
            </div>
            <div className="absolute left-14 right-0 top-0 bottom-6">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible">
                <defs>
                  <linearGradient id="chart-grad" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" /><stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                  </linearGradient>
                </defs>
                {hasHistory ? (
                  <>
                    <path d={toPath(highestBoundData)} fill="none" stroke="#f59e0b" strokeOpacity="0.5" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                    <path d={toPath(lowestBoundData)} fill="none" stroke="#f43f5e" strokeOpacity="0.5" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                    <path d={toPath(targets)} fill="none" stroke="#10b981" strokeWidth="1" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
                    <path d={`${toPath(prices)} L 100 100 L 0 100 Z`} fill="url(#chart-grad)" />
                    <path d={toPath(prices)} fill="none" stroke="#3b82f6" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
                  </>
                ) : <text x="50" y="50" fill="#64748b" fontSize="4" textAnchor="middle" alignmentBaseline="middle">Gathering Multi-Day History (Day 1)...</text>}
              </svg>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-[#10142b]/80 border border-indigo-500/20 rounded-3xl p-6 shadow-xl relative overflow-hidden group">
            <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[50px] bg-indigo-500/20 pointer-events-none"></div>
            <Activity className="text-indigo-400 mb-3" size={24} />
            <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mb-1">Deepest Discount</p>
            <p className="text-3xl font-bold text-white mb-2">+{deepestDiscount.toFixed(1)}%</p>
            <p className="text-xs text-indigo-300">Lowest drop below analyst target price in selected timeframe.</p>
          </div>
          <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-6 shadow-xl">
            <TrendingUp className="text-emerald-400 mb-3" size={24} />
            <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mb-1">Peak Price</p>
            <p className="text-3xl font-bold text-white mb-2">${peakPrice.toFixed(2)}</p>
            <p className="text-xs text-emerald-500/80">Highest closing price recorded in selected timeframe.</p>
          </div>
          <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-6 shadow-xl grid grid-cols-2 gap-4">
            <div><p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Latest Close</p><p className="font-bold text-slate-200">${(stock.close || 0).toFixed(2)}</p></div>
            <div><p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Mean Target</p><p className="font-bold text-emerald-400">${(stock.target || 0).toFixed(2)}</p></div>
            <div><p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">P/E Ratio</p><p className="font-bold text-slate-200">{stock.peRatio > 0 ? stock.peRatio.toFixed(2) : 'N/A'}</p></div>
            <div><p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">Current Upside</p><p className={`font-bold ${stock.upside > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{stock.upside > 0 ? '+' : ''}{stock.upside.toFixed(1)}%</p></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AINewsEngine({ savedStocks, watchList, data }) {
  const [selectedTicker, setSelectedTicker] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [showDiff, setShowDiff] = useState(true);

  const combinedAssets = useMemo(() => [...new Set([...savedStocks, ...watchList])], [savedStocks, watchList]);

  useEffect(() => {
    if (combinedAssets.length > 0 && (!selectedTicker || !combinedAssets.includes(selectedTicker))) {
      setSelectedTicker(combinedAssets[0]);
    }
  }, [combinedAssets, selectedTicker]);

  useEffect(() => {
    if (!selectedTicker) return;
    const fetchExistingReport = async () => {
      setIsLoadingReport(true);
      try {
        const res = await fetch(`${S3_BUCKET_URL}/dashboard/research/${selectedTicker}_latest.json?t=${Date.now()}`);
        if (res.ok) {
          const existingData = await res.json();
          setReportData(existingData);
        } else {
          setReportData(null);
        }
      } catch (err) {
        setReportData(null);
      }
      setIsLoadingReport(false);
    };
    fetchExistingReport();
  }, [selectedTicker]);

  const runResearchPipeline = async () => {
    if (!selectedTicker) return;
    setIsAnalyzing(true);
    
    try {
      const response = await fetch(LAMBDA_RESEARCH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: selectedTicker })
      });
      
      const newData = await response.json();
      
      if (response.ok) {
        setReportData(newData);
      } else {
        console.error("[AWS Lambda Error]:", newData);
        alert("Lambda failed to generate report. Check console.");
      }
    } catch (err) {
      console.error("[Fetch Error]: Failed to reach Lambda", err);
    }
    
    setIsAnalyzing(false);
  };

  if (!combinedAssets || combinedAssets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-slide-up text-center">
        <div className="w-24 h-24 rounded-full bg-[#111c38]/80 border border-purple-500/30 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(168,85,247,0.2)]">
          <Newspaper size={40} className="text-purple-400" />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">Research Queue Empty</h2>
        <p className="text-slate-400 max-w-md">Add assets to your Portfolio or Pipeline to run deep institutional research reports.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl space-y-6 animate-slide-up" style={{ animationDuration: '0.3s' }}>
      <div className="flex flex-col md:flex-row justify-between md:items-center bg-[#0d0b1a]/80 backdrop-blur-2xl border border-[#2d254f]/50 p-6 rounded-3xl shadow-xl shadow-black/40 gap-4">
        <div>
           <div className="flex items-center gap-3 mb-1">
             <h2 className="text-2xl font-serif font-medium text-amber-50/90 tracking-wide flex items-center gap-3 drop-shadow-sm">
               <Newspaper size={24} className="text-amber-400/80" /> Baseline Context Engine
             </h2>
           </div>
           <p className="text-sm text-slate-400 mt-1">Comparing live news sentiment against stored S3 thesis reports.</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5 ml-1">Target Asset</label>
            <select 
              className="w-full md:w-48 bg-[#111c38]/90 border border-[#1e3a8a]/50 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 shadow-inner appearance-none cursor-pointer"
              value={selectedTicker}
              onChange={(e) => setSelectedTicker(e.target.value)}
            >
              {combinedAssets.map(t => <option key={`res-${t}`} value={t}>{t}</option>)}
            </select>
            <ChevronRight size={16} className="absolute right-4 bottom-3 text-slate-400 pointer-events-none rotate-90" />
          </div>
          <button 
            onClick={runResearchPipeline}
            disabled={isAnalyzing || isLoadingReport}
            className="mt-5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium transition-all shadow-[0_0_20px_rgba(126,34,206,0.3)] hover:shadow-[0_0_25px_rgba(126,34,206,0.5)] border border-purple-400/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? <><Loader2 size={18} className="animate-spin" /> Orchestrating...</> : <><Sparkles size={18} /> Run Research</>}
          </button>
        </div>
      </div>

      {isLoadingReport && !isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
           <Loader2 className="w-8 h-8 animate-spin mb-4 text-purple-500/50" />
           <p>Checking S3 for baseline report...</p>
        </div>
      )}

      {!isLoadingReport && !reportData && !isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-[#0d0b1a]/40 rounded-3xl border border-[#2d254f]/30 border-dashed">
           <Newspaper className="w-12 h-12 mb-4 text-slate-600" />
           <p className="text-lg text-white font-medium">No Baseline Found</p>
           <p className="text-sm">Click 'Run Research' to generate the initial S3 report for {selectedTicker}.</p>
        </div>
      )}

      {isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-20 animate-pulse">
          <div className="w-16 h-16 rounded-full bg-purple-500/20 border-2 border-purple-500/50 flex items-center justify-center mb-6">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Orchestrating AI Agents...</h3>
          <p className="text-slate-400 text-sm">1. Fetching previous baseline report from S3</p>
          <p className="text-slate-400 text-sm">2. Scraping live financial news for {selectedTicker}</p>
          <p className="text-slate-400 text-sm">3. Synthesizing thesis delta...</p>
        </div>
      )}

      {reportData && !isAnalyzing && (
        <div className="space-y-6 animate-slide-up">
          <div className={`p-8 rounded-3xl border backdrop-blur-2xl relative overflow-hidden shadow-xl shadow-black/40 flex flex-col md:flex-row justify-between items-center gap-6 ${
            reportData.verdict === 'Temporary Overreaction' ? 'bg-[#062417]/80 border-emerald-500/30' : 
            reportData.verdict === 'Permanent Failure' ? 'bg-[#2b101a]/80 border-rose-500/30' : 
            'bg-[#1a170b]/80 border-amber-500/30'
          }`}>
            <div className={`absolute -top-20 -right-20 w-64 h-64 rounded-full blur-[80px] pointer-events-none opacity-40 ${
              reportData.verdict === 'Temporary Overreaction' ? 'bg-emerald-500' : 
              reportData.verdict === 'Permanent Failure' ? 'bg-rose-500' : 
              'bg-amber-500'
            }`}></div>
            
            <div className="relative z-10">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-2">
                 Institutional Thesis Verdict
              </p>
              <h2 className={`text-4xl font-bold tracking-tight mb-2 ${
                reportData.verdict === 'Temporary Overreaction' ? 'text-emerald-400' : 
                reportData.verdict === 'Permanent Failure' ? 'text-rose-400' : 
                'text-amber-400'
              }`}>
                {reportData.verdict}
              </h2>
              <p className="text-slate-300 font-medium">{reportData.thesisShift}</p>
            </div>
            
            <div className="relative z-10 flex flex-col items-end">
              <div className="text-center px-6 py-3 bg-[#07050f]/60 rounded-2xl border border-white/10 backdrop-blur-md">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">AI Confidence</p>
                <p className="text-3xl font-bold text-white">{reportData.confidence}%</p>
              </div>
              <p className="text-[10px] text-slate-500 mt-3 flex items-center gap-1.5">
                Baseline Comparison: {reportData.lastBaseline}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between px-2">
             <h3 className="text-lg font-serif font-medium text-slate-200">The Delta Matrix</h3>
             <label className="flex items-center cursor-pointer">
                <div className="relative">
                  <input type="checkbox" className="sr-only" checked={showDiff} onChange={() => setShowDiff(!showDiff)} />
                  <div className={`block w-10 h-6 rounded-full transition-colors ${showDiff ? 'bg-purple-600' : 'bg-slate-700'}`}></div>
                  <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${showDiff ? 'transform translate-x-4' : ''}`}></div>
                </div>
                <div className="ml-3 text-sm font-medium text-slate-400">Highlight Changes</div>
             </label>
          </div>

          <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl overflow-hidden backdrop-blur-xl shadow-xl">
            <div className="grid grid-cols-1 md:grid-cols-3 bg-[#111c38]/80 border-b border-[#2d254f]/50 text-xs uppercase tracking-wider font-bold text-slate-400 p-4">
              <div>S3 Baseline Thesis</div>
              <div>Current Live Catalyst</div>
              <div>AI Delta Assessment</div>
            </div>
            <div className="divide-y divide-[#2d254f]/30">
              {reportData.deltaMatrix && reportData.deltaMatrix.map((row, idx) => (
                <div key={idx} className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 hover:bg-[#16122b]/40 transition-colors">
                  <div className="text-sm text-slate-300 pr-4">{row.baseline}</div>
                  <div className="text-sm text-white pr-4 relative">
                    {row.current}
                    {showDiff && row.type === 'Negative' && <span className="absolute -left-2 top-1 w-1 h-full bg-rose-500 rounded-full shadow-[0_0_8px_rgba(244,63,94,0.6)]"></span>}
                    {showDiff && row.type === 'Positive' && <span className="absolute -left-2 top-1 w-1 h-full bg-emerald-500 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.6)]"></span>}
                  </div>
                  <div className="text-sm font-medium">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider mr-2 border ${
                      row.type === 'Temporary' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' :
                      row.type === 'Positive' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                      row.type === 'Negative' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                      'bg-slate-500/10 text-slate-400 border-slate-500/30'
                    }`}>
                      {row.type}
                    </span>
                    <span className="text-slate-300">{row.assessment}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#1a0f14]/80 border border-rose-500/20 rounded-3xl p-6 backdrop-blur-xl shadow-xl">
              <h3 className="text-rose-400 font-bold uppercase tracking-wider text-sm mb-4 flex items-center gap-2">
                <AlertTriangle size={16} /> Structural Risks (Permanent Drop)
              </h3>
              <ul className="space-y-3">
                {reportData.structuralRisks && reportData.structuralRisks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                    <div className="mt-1 w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0 shadow-[0_0_5px_rgba(244,63,94,0.8)]"></div>
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="bg-[#0a1a14]/80 border border-emerald-500/20 rounded-3xl p-6 backdrop-blur-xl shadow-xl">
              <h3 className="text-emerald-400 font-bold uppercase tracking-wider text-sm mb-4 flex items-center gap-2">
                <TrendingUp size={16} /> Noise & Transitory Factors (Buy-The-Dip)
              </h3>
              <ul className="space-y-3">
                {reportData.transitoryFactors && reportData.transitoryFactors.map((factor, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                    <div className="mt-1 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 shadow-[0_0_5px_rgba(16,185,129,0.8)]"></div>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="bg-[#0d0b1a]/80 border border-[#2d254f]/50 rounded-3xl p-6 backdrop-blur-xl shadow-xl">
            <h3 className="text-slate-200 font-serif font-medium text-lg mb-6">Catalyst Timeline</h3>
            <div className="relative border-l-2 border-[#2d254f]/50 ml-3 space-y-6 pb-2">
              {reportData.timeline && reportData.timeline.map((item, i) => (
                <div key={i} className="relative pl-6">
                  <div className={`absolute -left-[5px] top-1.5 w-2 h-2 rounded-full ring-4 ring-[#0d0b1a] ${
                    item.impact === 'Negative' ? 'bg-rose-500' :
                    item.impact === 'Positive' ? 'bg-emerald-500' : 'bg-slate-500'
                  }`}></div>
                  <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase mb-0.5">{item.date}</div>
                  <div className="text-sm text-slate-300">{item.event}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}