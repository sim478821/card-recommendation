import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';
import './App.css';

function App() {
  const [showModal, setShowModal] = useState(true);
  const [showRanking, setShowRanking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  
  const [fileName, setFileName] = useState(""); 
  const [selectedFile, setSelectedFile] = useState(null); 

  const [rankings, setRankings] = useState([]); 
  const [summary, setSummary] = useState({}); 
  const [recommendations, setRecommendations] = useState([]); 
  const [selectedCombo, setSelectedCombo] = useState(null); 

  const [filters, setFilters] = useState({
    cardCompany: '전체 카드사',
    annualFee: '전체 연회비',
    performance: '전체 전월실적'
  });

  const fetchRankings = async () => {
    try {
      const res = await axios.get('https://card-recommendation.onrender.com/api/rankings');
      setRankings(res.data || []);
    } catch (error) {
      console.error("랭킹 로드 실패", error);
    }
  };

  useEffect(() => {
    fetchRankings();
  }, []);

  const analyzeFile = async (file, currentFilters) => {
    if (!file) return;
    setIsLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filters', JSON.stringify(currentFilters));

    try {
      const response = await axios.post('https://card-recommendation.onrender.com/api/analyze', formData);
      
      if (response.data?.error) {
        alert("에러: " + response.data.error);
        setIsLoading(false);
        return;
      }

      setSummary(response.data?.summary || {});
      setRecommendations(response.data?.recommendations || []);
      
      if (response.data?.recommendations && response.data.recommendations.length > 0) {
        setSelectedCombo(response.data.recommendations[0]);
      } else {
        setSelectedCombo(null); 
      }
      
      setShowResults(true);
      fetchRankings(); 
      
    } catch (error) {
      alert("서버 연결 실패! 백엔드 uvicorn 서버 상태를 확인하세요.");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFile) {
      analyzeFile(selectedFile, filters);
    }
  }, [filters]);

  const onDrop = async (acceptedFiles) => {
    if (!acceptedFiles || acceptedFiles.length === 0) return;
    
    const file = acceptedFiles[0];
    setFileName(file.name || "알 수 없는 파일");
    setSelectedFile(file); 

    await analyzeFile(file, filters);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: 'application/pdf' });

  return (
    <div className="app-container">
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-paper" onClick={(e) => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            <div className="modal-content">
              <h2 className="modal-title">서비스 이용 안내</h2>
              <ol className="modal-list">
                <li>원하는 카드사와 연회비, 전월실적 기준을 선택하세요.</li>
                <li>소비내역명세서 PDF 파일을 첨부하세요.</li>
                <li>5가지의 최적 추천 조합이 생성됩니다. 각 조합을 클릭하여 세부 사항을 확인해보세요.</li>
              </ol>
            </div>
          </div>
        </div>
      )}

      <header className="app-header">
        <div className="filters-container">
          <select value={filters.cardCompany} onChange={(e) => setFilters({ ...filters, cardCompany: e.target.value })}>
            <option>전체 카드사</option><option>삼성카드</option><option>신한카드</option><option>현대카드</option><option>KB국민카드</option>
            <option>롯데카드</option><option>우리카드</option><option>하나카드</option><option>NH농협카드</option><option>IBK기업은행</option>
          </select>
          <select value={filters.annualFee} onChange={(e) => setFilters({ ...filters, annualFee: e.target.value })}>
            <option>전체 연회비</option><option>0원</option><option>1만원</option><option>3만원</option><option>5만원</option><option>10만원</option><option>10만원 이상</option>
          </select>
          <select value={filters.performance} onChange={(e) => setFilters({ ...filters, performance: e.target.value })}>
            <option>전체 전월실적</option><option>0원</option><option>30만원</option><option>50만원</option><option>50만원 이상</option>
          </select>
        </div>

        <div className="ranking-container">
          <button className="ranking-btn" onClick={() => setShowRanking(!showRanking)}>
            🏆 신용카드 인기 순위 {showRanking ? '▲' : '▼'}
          </button>
          {showRanking && (
            <ul className="ranking-dropdown">
              {rankings && rankings.length > 0 ? rankings.map((rank, index) => (
                <li key={rank.name}>
                  <strong>{index + 1}위</strong> {rank.name} <span className="rank-count">({rank.count}회)</span>
                </li>
              )) : <li><span className="rank-count">랭킹 데이터가 없습니다.</span></li>}
            </ul>
          )}
        </div>
      </header>

      {!showResults ? (
        <main className="upload-main">
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            {isLoading ? (
              <div className="loading-content">
                <div className="spinner"></div>
                <p>소비 패턴을 분석하고 최적의 신용카드 조합을 계산합니다.</p>
                {fileName && (
                  <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#eef2ff', color: '#3b82f6', borderRadius: '8px', fontWeight: 'bold' }}>
                    ✅ 분석 중인 파일: {fileName}
                  </div>
                )}
              </div>
            ) : (
              <div className="upload-content">
                <div className="upload-icon">📄</div>
                <h3>이용대금 명세서 PDF 첨부</h3>
                <p>파일을 끌어다 놓거나 클릭하여 업로드하세요</p>
              </div>
            )}
          </div>
        </main>
      ) : (
        <main className="results-main">
          <section className="summary-section">
            <h3>
              📊 명세서 분석 요약 
              {fileName && <span style={{ fontSize: '15px', color: '#64748b', fontWeight: 'normal', marginLeft: '10px' }}>({fileName})</span>}
            </h3>
            <div className="summary-cards">
              {Object.entries(summary || {}).map(([category, amount]) => (
                <div className="summary-card" key={category}>
                  <h4>{category}</h4>
                  <p>{amount.toLocaleString()}원</p>
                </div>
              ))}
            </div>
          </section>

          <div className="results-layout">
            <section className="recommendation-list">
              <h3>💳 추천 신용카드 조합 TOP 5</h3>
              {recommendations && recommendations.length > 0 ? recommendations.map((combo, index) => (
                <div 
                  key={combo.id} 
                  className={`recommend-item ${selectedCombo && selectedCombo.id === combo.id ? 'selected' : ''}`}
                  onClick={() => setSelectedCombo(combo)}
                >
                  <div className="rank-badge">{index + 1}</div>
                  <div className="card-info">
                    <h4 style={{fontSize: '15px'}}>{combo.cards[0]}<br/>+ {combo.cards[1]}</h4>
                    <p className="discount-text">총 절약 금액: <strong>{combo.totalDiscount.toLocaleString()}원</strong></p>
                  </div>
                </div>
              )) : (
                <div className="empty-selection" style={{ padding: '20px', background: 'white', borderRadius: '12px', textAlign: 'center' }}>
                  <p>선택하신 필터 조합을 만족하는 카드가 카드사 DB에 없습니다.</p>
                </div>
              )}
            </section>

            <section className="detail-view">
              {selectedCombo ? (
                <>
                  <h3>세부 절약 내역 ({selectedCombo?.cards?.join(' & ')})</h3>
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>카테고리</th>
                        <th>할인 전</th>
                        <th>할인 후</th>
                        <th>절약</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedCombo?.chartData?.map((data, idx) => (
                        <tr key={idx}>
                          <td>{data.category}</td>
                          <td>{data.beforeDiscount.toLocaleString()}원</td>
                          <td>{data.afterDiscount.toLocaleString()}원</td>
                          <td className="highlight-save">{(data.beforeDiscount - data.afterDiscount).toLocaleString()}원</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <h3 className="chart-title">소비 비교 (할인 전 vs 할인 후)</h3>
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={selectedCombo?.chartData || []}>
                        <XAxis dataKey="category" />
                        <YAxis />
                        <Tooltip formatter={(value) => `${value.toLocaleString()}원`} />
                        <Legend />
                        <Bar dataKey="beforeDiscount" fill="#cbd5e1" name="할인 전" />
                        <Bar dataKey="afterDiscount" fill="#3b82f6" name="할인 후" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              ) : (
                <div className="empty-selection">
                  <p>좌측에서 추천 조합을 선택하면 상세 정보가 나타납니다.</p>
                </div>
              )}
            </section>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;