'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { config } from '../config';

export default function Results() {
  const [results, setResults] = useState<any>({
    monthly: { for: 0, against: 0 },
    biweekly: { for: 0, against: 0 }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await axios.get(`${config.apiUrl}/api/results`);
        if (response.data && response.data.results) {
          setResults(response.data.results);
        } else {
          setResults(response.data || {});
        }
        setLoading(false);
      } catch (err) {
        setError('결과를 불러오는 중 오류가 발생했습니다.');
        setLoading(false);
        console.error(err);
      }
    };

    fetchResults();
  }, []);

  const containerStyle = {
    display: 'flex',
    minHeight: '100vh',
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: '1rem',
    background: '#f5f5f5'
  };

  const cardStyle = {
    width: '100%',
    maxWidth: '500px',
    background: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
  };

  const titleStyle = {
    fontSize: '1.5rem',
    fontWeight: 'bold' as const,
    textAlign: 'center' as const,
    marginBottom: '1.5rem'
  };

  const buttonStyle = {
    width: '100%',
    background: '#3b82f6',
    color: 'white',
    fontWeight: 'bold' as const,
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginTop: '1.5rem'
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <h1 style={titleStyle}>투표 결과 로딩 중...</h1>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <h1 style={titleStyle}>오류 발생</h1>
          <p style={{textAlign: 'center', marginBottom: '1rem'}}>{error}</p>
          <button
            onClick={() => window.location.reload()}
            style={buttonStyle}
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  // 결과 데이터 정리
  const monthlyFor = results.monthly?.for || 0;
  const monthlyAgainst = results.monthly?.against || 0;
  const biweeklyFor = results.biweekly?.for || 0;
  const biweeklyAgainst = results.biweekly?.against || 0;

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>투표 결과</h1>

        <div style={{marginBottom: '2rem'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.75rem'}}>월 1회 회식</h2>    

          <div style={{marginBottom: '1rem'}}>
            <p style={{marginBottom: '0.5rem'}}>찬성: {monthlyFor}표</p>
            <div style={{height: '20px', background: '#eee', borderRadius: '10px', overflow: 'hidden'}}>    
              <div
                style={{
                  height: '100%',
                  width: `${(monthlyFor / (monthlyFor + monthlyAgainst || 1)) * 100}%`,
                  background: '#4299e1'
                }}
              />
            </div>
          </div>

          <div>
            <p style={{marginBottom: '0.5rem'}}>반대: {monthlyAgainst}표</p>
            <div style={{height: '20px', background: '#eee', borderRadius: '10px', overflow: 'hidden'}}>    
              <div
                style={{
                  height: '100%',
                  width: `${(monthlyAgainst / (monthlyFor + monthlyAgainst || 1)) * 100}%`,
                  background: '#f56565'
                }}
              />
            </div>
          </div>
        </div>

        <div>
          <h2 style={{fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.75rem'}}>2주 1회 회식</h2>   

          <div style={{marginBottom: '1rem'}}>
            <p style={{marginBottom: '0.5rem'}}>찬성: {biweeklyFor}표</p>
            <div style={{height: '20px', background: '#eee', borderRadius: '10px', overflow: 'hidden'}}>    
              <div
                style={{
                  height: '100%',
                  width: `${(biweeklyFor / (biweeklyFor + biweeklyAgainst || 1)) * 100}%`,
                  background: '#4299e1'
                }}
              />
            </div>
          </div>

          <div>
            <p style={{marginBottom: '0.5rem'}}>반대: {biweeklyAgainst}표</p>
            <div style={{height: '20px', background: '#eee', borderRadius: '10px', overflow: 'hidden'}}>    
              <div
                style={{
                  height: '100%',
                  width: `${(biweeklyAgainst / (biweeklyFor + biweeklyAgainst || 1)) * 100}%`,
                  background: '#f56565'
                }}
              />
            </div>
          </div>
        </div>

        <button
          onClick={() => window.location.href = '/'}
          style={buttonStyle}
        >
          투표 페이지로 돌아가기
        </button>
      </div>
    </div>
  );
} 