'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { config } from './config';

export default function Home() {
  const [hasVoted, setHasVoted] = useState(false);
  const [monthly, setMonthly] = useState<'for' | 'against' | null>(null);
  const [biweekly, setBiweekly] = useState<'for' | 'against' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // 로컬 스토리지에서 투표 여부 확인
    const voted = localStorage.getItem('hasVoted');
    if (voted === 'true') {
      setHasVoted(true);
    }
  }, []);

  const handleVote = async () => {
    if (!monthly || !biweekly) {
      setError('두 옵션 모두 선택해주세요.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 사용자 ID 생성
      const userId = 'anonymous-' + Math.random().toString(36).substring(2, 9);
      
      // 월 1회 회식에 대한 투표
      await axios.post(`${config.apiUrl || "http://172.16.1.17:8000"}/api/vote`, {
        user_id: userId + '-monthly',
        candidate_id: 'monthly',
        vote_type: monthly
      });
      
      // 2주 1회 회식에 대한 투표
      await axios.post(`${config.apiUrl || "http://172.16.1.17:8000"}/api/vote`, {
        user_id: userId + '-biweekly',
        candidate_id: 'biweekly',
        vote_type: biweekly
      });

      // 투표 완료 후 로컬 스토리지에 저장
      localStorage.setItem('hasVoted', 'true');
      setHasVoted(true);
    } catch (err) {
      setError('투표 중 오류가 발생했습니다. 다시 시도해주세요.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const containerStyle = {
    display: 'flex',
    minHeight: '100vh',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
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
    fontWeight: 'bold',
    textAlign: 'center' as const,
    marginBottom: '1.5rem'
  };

  const buttonStyle = {
    width: '100%',
    background: '#3b82f6',
    color: 'white',
    fontWeight: 'bold',
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  };

  if (hasVoted) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <h1 style={titleStyle}>투표 완료</h1>
          <p style={{textAlign: 'center', marginBottom: '1rem'}}>
            이미 투표를 완료하셨습니다. 감사합니다!
          </p>
          <button
            onClick={() => window.location.href = '/results'}
            style={buttonStyle}
          >
            결과 보기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>회식 주기 투표</h1>

        <div style={{marginBottom: '1.5rem'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.75rem'}}>월 1회 회식</h2>    
          <div style={{display: 'flex', gap: '1rem'}}>
            <button
              onClick={() => setMonthly('for')}
              style={{
                flex: '1',
                padding: '0.5rem 1rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                background: monthly === 'for' ? '#4299e1' : '#f5f5f5',
                color: monthly === 'for' ? 'white' : 'inherit',
                cursor: 'pointer'
              }}
            >
              찬성
            </button>
            <button
              onClick={() => setMonthly('against')}
              style={{
                flex: '1',
                padding: '0.5rem 1rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                background: monthly === 'against' ? '#4299e1' : '#f5f5f5',
                color: monthly === 'against' ? 'white' : 'inherit',
                cursor: 'pointer'
              }}
            >
              반대
            </button>
          </div>
        </div>

        <div style={{marginBottom: '1.5rem'}}>
          <h2 style={{fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.75rem'}}>2주 1회 회식</h2>   
          <div style={{display: 'flex', gap: '1rem'}}>
            <button
              onClick={() => setBiweekly('for')}
              style={{
                flex: '1',
                padding: '0.5rem 1rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                background: biweekly === 'for' ? '#4299e1' : '#f5f5f5',
                color: biweekly === 'for' ? 'white' : 'inherit',
                cursor: 'pointer'
              }}
            >
              찬성
            </button>
            <button
              onClick={() => setBiweekly('against')}
              style={{
                flex: '1',
                padding: '0.5rem 1rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                background: biweekly === 'against' ? '#4299e1' : '#f5f5f5',
                color: biweekly === 'against' ? 'white' : 'inherit',
                cursor: 'pointer'
              }}
            >
              반대
            </button>
          </div>
        </div>

        {error && (
          <div style={{color: '#e53e3e', textAlign: 'center', marginBottom: '1rem'}}>
            {error}
          </div>
        )}

        <button
          onClick={handleVote}
          disabled={loading}
          style={{
            ...buttonStyle,
            opacity: loading ? '0.5' : '1'
          }}
        >
          {loading ? '처리 중...' : '투표하기'}
        </button>
      </div>
    </div>
  );
} 