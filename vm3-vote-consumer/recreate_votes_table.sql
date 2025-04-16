-- 기존 테이블 삭제 (있는 경우)
DROP TABLE IF EXISTS votes;

-- 새 테이블 생성
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    candidate_id VARCHAR(50) NOT NULL,
    vote_time TIMESTAMP NOT NULL,
    message_id VARCHAR(100) NOT NULL,
    vote_type VARCHAR(20) NOT NULL DEFAULT 'for',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 고유 제약 조건 추가
ALTER TABLE votes ADD CONSTRAINT votes_message_id_key UNIQUE (message_id);

-- 인덱스 생성
CREATE INDEX idx_votes_candidate_id ON votes(candidate_id);
CREATE INDEX idx_votes_vote_type ON votes(vote_type);

-- 확인 메시지
SELECT 'votes 테이블이 성공적으로 재생성되었습니다.' AS message; 