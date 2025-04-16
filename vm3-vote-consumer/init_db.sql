-- 테이블이 없으면 생성
CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    candidate_id VARCHAR(50) NOT NULL,
    vote_time TIMESTAMP NOT NULL,
    message_id VARCHAR(100) NOT NULL,
    vote_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- message_id에 고유 제약 조건 추가 (중복 방지)
-- 이미 인덱스가 있는 경우 에러가 발생하지 않도록 조건부로 생성
DO $$
BEGIN
    -- message_id에 UNIQUE 제약 조건이 없는 경우에만 추가
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'votes_message_id_key' AND conrelid = 'votes'::regclass
    ) THEN
        ALTER TABLE votes ADD CONSTRAINT votes_message_id_key UNIQUE (message_id);
    END IF;
END
$$;

-- 추가 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_votes_candidate_id ON votes(candidate_id);
CREATE INDEX IF NOT EXISTS idx_votes_vote_type ON votes(vote_type);

-- 테스트용 데이터 삽입 (선택 사항)
-- INSERT INTO votes (user_id, candidate_id, vote_time, message_id, vote_type)
-- VALUES 
--   ('test-user-1', 'monthly', NOW(), 'test-message-1', 'for'),
--   ('test-user-2', 'biweekly', NOW(), 'test-message-2', 'against'); 