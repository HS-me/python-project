-- 테이블에 vote_type 열 추가
ALTER TABLE votes ADD COLUMN IF NOT EXISTS vote_type VARCHAR(20) DEFAULT 'for' NOT NULL;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_votes_vote_type ON votes(vote_type);

-- 확인 메시지 출력
SELECT 'vote_type 열이 성공적으로 추가되었습니다.' AS message; 