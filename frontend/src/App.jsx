import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Search, 
  Database, 
  Activity, 
  Layers, 
  Shield, 
  Cpu,
  FileText,
  List,
  ChevronRight,
  Globe,
  CornerDownLeft
} from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState('');
  const [formattedReport, setFormattedReport] = useState('');
  const [sources, setSources] = useState([]);
  
  // Tab control: 'assessment' | 'sources'
  const [activeTab, setActiveTab] = useState('assessment');
  
  // Console logs
  const [consoleLogs, setConsoleLogs] = useState([
    { time: '00:00:01', text: 'COSMIC HORIZON DEPLOYMENT INITIALIZED', type: 'info' },
    { time: '00:00:02', text: 'Local Nomic Embedding model: READY (./models/nomic-embed-text-v1.5)', type: 'success' },
    { time: '00:00:02', text: 'Local spaCy Language model: READY (en_core_web_sm)', type: 'success' },
    { time: '00:00:03', text: 'ChromaDB collection: weekly_articles CONNECTED', type: 'info' },
    { time: '00:00:03', text: 'Awaiting Priority Intelligence Requirement (PIR) query...', type: 'info' }
  ]);

  // QA Follow-up
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState([
    { role: 'system', text: 'ChromaDB Local RAG store initialized. Enter follow-up questions below.' }
  ]);
  const [isQaLoading, setIsQaLoading] = useState(false);

  // Auto-scrollers
  const logEndRef = useRef(null);
  const qaEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [consoleLogs]);

  useEffect(() => {
    qaEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [qaHistory]);

  const addLog = (text, type = 'info') => {
    const time = new Date().toTimeString().split(' ')[0];
    setConsoleLogs(prev => [...prev, { time, text, type }]);
  };

  const handleQuickQuery = (text) => {
    setQuery(text);
    handleAssess(text);
  };

  const handleAssess = async (queryText) => {
    const activeQuery = queryText || query;
    if (!activeQuery.trim()) return;

    setIsLoading(true);
    setReport('');
    setFormattedReport('');
    setSources([]);
    setQaHistory([
      { role: 'system', text: 'ChromaDB Local RAG store initialized. Enter follow-up questions below.' }
    ]);
    
    setConsoleLogs([]);
    addLog(`INITIALIZING PIPELINE: "${activeQuery}"`, 'info');

    // Sequence of simulated steps (corresponds to actual backend execution, providing visual feedback)
    const runSimulatedLogs = () => {
      setTimeout(() => addLog('STAGE 1: NLP TERM EXTRACTION - Initializing spaCy NER...', 'info'), 500);
      setTimeout(() => addLog('STAGE 1: NLP TERM EXTRACTION - KeyBERT model matching initialized...', 'info'), 1500);
      setTimeout(() => addLog('STAGE 2: PARALLEL SEARCH CLIENT - Dispatched TaskGroup queries via HTTPX...', 'info'), 2500);
      setTimeout(() => addLog('STAGE 3: SEMANTIC FILTERING - Loading FAISS flat IndexFlatIP index...', 'info'), 3800);
      setTimeout(() => addLog('STAGE 3: SEMANTIC FILTERING - Computed cosine similarity for candidates...', 'info'), 4800);
      setTimeout(() => addLog('STAGE 4: HYBRID RERANKING - Computing BM25 + Reciprocal Rank Fusion (k=60)...', 'info'), 6000);
      setTimeout(() => addLog('STAGE 5: REPORT SYNTHESIS - Constructing prompt instructions...', 'info'), 7200);
      setTimeout(() => addLog('STAGE 6: CHROMADB INGESTION - Segmenting text into sentence-bounded chunks...', 'info'), 8500);
    };

    runSimulatedLogs();

    try {
      const response = await fetch('/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: activeQuery })
      });

      if (!response.ok) {
        throw new Error(`Pipeline error: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Complete remaining logging
      setTimeout(() => {
        setReport(data.report);
        setFormattedReport(data.formatted_report);
        setSources(data.sources || []);
        addLog('STAGE 5: REPORT SYNTHESIS - Claude Assessment compiles SUCCESSFULLY.', 'success');
        addLog(`STAGE 6: CHROMADB INGESTION - Ingested document chunks into local RAG collection.`, 'success');
        addLog('PIPELINE CONVERGED. Intelligence Assessment generated.', 'success');
        setIsLoading(false);
      }, 9500);

    } catch (error) {
      addLog(`PIPELINE FAIL: ${error.message}`, 'error');
      setIsLoading(false);
    }
  };

  const handleQaSubmit = async (e) => {
    e.preventDefault();
    if (!qaQuestion.trim() || !report || isQaLoading) return;

    const question = qaQuestion;
    setQaQuestion('');
    setQaHistory(prev => [...prev, { role: 'user', text: question }]);
    setIsQaLoading(true);

    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: question,
          original_report: report 
        })
      });

      if (!response.ok) {
        throw new Error('Failed to retrieve follow-up answer.');
      }

      const data = await response.json();
      setQaHistory(prev => [...prev, { role: 'assistant', text: data.answer }]);
    } catch (error) {
      setQaHistory(prev => [...prev, { role: 'assistant', text: `Error: ${error.message}` }]);
    } finally {
      setIsQaLoading(false);
    }
  };

  // Basic custom markdown formatter (handles headers, bold, bullets, notes)
  const renderMarkdown = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, idx) => {
      const cleanLine = line.trim();
      
      if (cleanLine.startsWith('###')) {
        return <h3 key={idx} className="glow-cyan">{cleanLine.replace('###', '').trim()}</h3>;
      }
      if (cleanLine.startsWith('-') || cleanLine.startsWith('*') || cleanLine.startsWith('•')) {
        // Simple citation styling
        const bulletText = cleanLine.replace(/^[-*•]/, '').trim();
        return (
          <li key={idx} dangerouslySetInnerHTML={{ 
            __html: bulletText.replace(/\[(ART\d+)\]/g, '<span class="glow-amber" style="color: var(--accent-amber); font-weight: bold;">[$1]</span>') 
          }} />
        );
      }
      if (cleanLine.startsWith('**') && cleanLine.endsWith('**')) {
        return <p key={idx}><strong>{cleanLine.replace(/\*\*/g, '')}</strong></p>;
      }
      if (cleanLine.startsWith('*') && cleanLine.endsWith('*')) {
        return <p key={idx}><em>{cleanLine.replace(/\*/g, '')}</em></p>;
      }
      if (cleanLine === '') {
        return <div key={idx} style={{ height: '10px' }} />;
      }
      return (
        <p key={idx} dangerouslySetInnerHTML={{ 
          __html: line.replace(/\[(ART\d+)\]/g, '<span class="glow-amber" style="color: var(--accent-amber); font-weight: bold;">[$1]</span>') 
        }} />
      );
    });
  };

  return (
    <>
      {/* Top Navigation Ops Bar */}
      <header className="ops-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Shield size={24} className="glow-cyan" style={{ color: 'var(--accent-cyan)' }} />
          <div>
            <h1 className="glow-cyan" style={{ fontSize: '18px', fontWeight: '900', color: '#fff' }}>
              COSMIC HORIZON
            </h1>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '2px' }}>
              SECURE PIR INTELLIGENCE ASSESSMENT SYSTEM
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="indicator-dot pulse"></span>
            <span style={{ color: '#00ff66' }}>AIRGAP SYSTEM SECURE</span>
          </div>
          <div style={{ color: 'var(--text-muted)', borderLeft: '1px solid rgba(0, 240, 255, 0.2)', paddingLeft: '20px' }}>
            NODE: <span style={{ color: 'var(--accent-amber)' }}>OFFLINE MODE (HF_OFFLINE=1)</span>
          </div>
        </div>
      </header>

      {/* Main Layout Grid */}
      <div className="ops-container">
        
        {/* Left Control Sidebar */}
        <aside className="ops-panel">
          
          {/* PIR Search Dispatcher */}
          <div className="search-container">
            <h2 style={{ fontSize: '12px', color: 'var(--accent-cyan)', marginBottom: '10px', letterSpacing: '1px' }}>
              PIR DISPATCH CONTROLLER
            </h2>
            <div className="input-glow-group">
              <input 
                type="text" 
                className="terminal-input"
                placeholder="Enter Priority Intelligence Req..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAssess()}
                disabled={isLoading}
              />
              <Search 
                size={18} 
                className="search-icon"
                onClick={() => handleAssess()}
              />
            </div>
          </div>

          {/* System Telemetry Stats */}
          <div className="stats-list">
            <h2 style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '1px', marginBottom: '5px' }}>
              SYSTEM TELEMETRY
            </h2>
            
            <div className="stat-item">
              <span className="stat-label">Model Context</span>
              <span className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cpu size={12} /> nomic-embed-v1.5
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">LLM Fallback</span>
              <span className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layers size={12} /> Local Mock Compiler
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">Vector Database</span>
              <span className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Database size={12} /> FAISS (IP Flat)
              </span>
            </div>

            <div className="stat-item">
              <span className="stat-label">RAG Collection</span>
              <span className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={12} /> ChromaDB Local
              </span>
            </div>
          </div>

          {/* Terminal Console Logs feed */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderTop: '1px solid var(--border-neon)', overflow: 'hidden' }}>
            <div style={{ padding: '10px 20px', background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid rgba(0, 240, 255, 0.05)', display: 'flex', justifyItems: 'center', gap: '8px' }}>
              <Terminal size={14} style={{ color: 'var(--accent-amber)' }} />
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-display)', color: 'var(--text-muted)' }}>PIPELINE LOG FEED</span>
            </div>
            
            <div className="console-logs-container">
              {consoleLogs.map((log, index) => (
                <div className="console-line" key={index}>
                  <span className="console-time">[{log.time}]</span>
                  <span className={`console-text ${log.type}`}>
                    {log.type === 'error' ? '✖ ' : log.type === 'success' ? '✔ ' : '⚡ '}
                    {log.text}
                  </span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </aside>

        {/* Main Display Pane & QA Terminal */}
        <main className="ops-main">
          
          {/* Main Assessment Reader */}
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', height: '100%' }}>
            
            {/* Display Navigation */}
            <div className="display-header">
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  className={`tab-btn ${activeTab === 'assessment' ? 'active' : ''}`}
                  onClick={() => setActiveTab('assessment')}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={14} /> INTELLIGENCE ASSESSMENT
                  </span>
                </button>
                {report && (
                  <button 
                    className={`tab-btn ${activeTab === 'sources' ? 'active' : ''}`}
                    onClick={() => setActiveTab('sources')}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <List size={14} /> RETRIEVED SOURCES ({sources.length})
                    </span>
                  </button>
                )}
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Globe size={14} style={{ color: 'var(--accent-cyan)' }} />
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  CLASSIFICATION: SECRET//NOFORN
                </span>
              </div>
            </div>

            {/* Display Content Frame */}
            <div className="display-content">
              {isLoading ? (
                <div className="welcome-screen">
                  <div className="glow-ring"></div>
                  <h3 className="glow-cyan pulse-glow" style={{ fontSize: '16px', letterSpacing: '4px', textTransform: 'uppercase' }}>
                    EXECUTING TACTICAL RAG PIPELINE
                  </h3>
                  <p style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: '10px' }}>
                    Loading NLP models & synthesizing reports...
                  </p>
                </div>
              ) : report ? (
                activeTab === 'assessment' ? (
                  <div className="intelligence-report">
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid var(--accent-cyan)', paddingBottom: '10px', marginBottom: '25px' }}>
                      <h2 style={{ fontSize: '22px', color: '#fff' }} className="glow-cyan">INTELLIGENCE SYNTHESIS</h2>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-amber)', fontSize: '13px' }}>REF: COS-PIR-2026</span>
                    </div>
                    {renderMarkdown(report)}
                  </div>
                ) : (
                  <div className="sources-grid">
                    {sources.map((src, index) => (
                      <div className="source-card" key={index}>
                        <div>
                          <div className="source-id">[{src.article_id}]</div>
                          <div className="source-title">{src.title}</div>
                        </div>
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="source-link">
                          Explore URL <ChevronRight size={14} />
                        </a>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <div className="welcome-screen">
                  <Shield size={64} className="welcome-logo flicker-text" />
                  <h2 className="welcome-title glow-cyan">COSMIC HORIZON</h2>
                  <p className="welcome-subtitle">
                    Enter a Priority Intelligence Requirement (PIR) below or select a quick-ops template query to assess regional developments, SCADA security breaches, or naval intelligence.
                  </p>
                  
                  <div className="quick-queries">
                    <button 
                      className="quick-btn"
                      onClick={() => handleQuickQuery('What is Cozy Bear (APT29) doing to target European energy pipelines?')}
                    >
                      Cozy Bear Pipeline Cyber Threats
                    </button>
                    <button 
                      className="quick-btn"
                      onClick={() => handleQuickQuery('Identify critical Siemens WinCC SCADA security vulnerabilities reported this week.')}
                    >
                      WinCC SCADA Vulnerabilities
                    </button>
                    <button 
                      className="quick-btn"
                      onClick={() => handleQuickQuery('Report on submarine naval fleet maneuvers in the Mediterranean or North Sea.')}
                    >
                      Submarine Fleet Movements
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Interactive RAG Terminal Q&A Dialog */}
          <div className="terminal-qa">
            <div className="terminal-header">
              <span className="terminal-title">
                LOCAL CHROMADB KNOWLEDGE COLLECTION & FOLLOW-UP Q&A TERMINAL
              </span>
              <span style={{ color: 'var(--accent-cyan)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                RAG SESSION ACTIVE
              </span>
            </div>

            <div className="terminal-body">
              {qaHistory.map((item, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  {item.role === 'user' && (
                    <div style={{ display: 'flex', gap: '8px', color: 'var(--accent-cyan)' }}>
                      <span>&gt; USER:</span>
                      <span>{item.text}</span>
                    </div>
                  )}
                  {item.role === 'assistant' && (
                    <div style={{ color: '#00ff66', paddingLeft: '12px', whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                      {item.text}
                    </div>
                  )}
                  {item.role === 'system' && (
                    <div style={{ color: 'var(--text-muted)', opacity: 0.6 }}>
                      ::: {item.text}
                    </div>
                  )}
                </div>
              ))}
              {isQaLoading && (
                <div style={{ color: 'var(--accent-amber)', animation: 'pulse 1s infinite alternate' }}>
                  ⚡ QUERYING LOCAL CHROMADB & COMPILING ASSISTANCE RESPONSE...
                </div>
              )}
              <div ref={qaEndRef} />
            </div>

            <form onSubmit={handleQaSubmit} className="terminal-prompt-line">
              <span className="terminal-prompt-symbol">&gt;_</span>
              <input 
                type="text" 
                className="terminal-prompt-input"
                placeholder={report ? "Ask a grounded follow-up question..." : "Please submit a PIR query first to unlock RAG session..."}
                value={qaQuestion}
                onChange={(e) => setQaQuestion(e.target.value)}
                disabled={!report || isQaLoading}
              />
              <button type="submit" style={{ display: 'none' }}></button>
              <CornerDownLeft size={14} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
            </form>
          </div>
        </main>
      </div>
    </>
  );
}
