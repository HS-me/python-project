import json
import logging
from kafka import KafkaConsumer
import redis
import os
import time
import sys
import signal
from datetime import datetime
import psycopg2
from psycopg2 import sql
import psycopg2.extras

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("consumer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SIGTERM 시그널 핸들러 (그레이스풀 셧다운용)
def handle_sigterm(*args):
    logger.info("SIGTERM 시그널 수신, 안전하게 종료합니다...")
    if hasattr(consumer, 'consumer') and consumer.consumer:
        logger.info("Kafka 컨슈머 연결을 명시적으로 종료합니다")
        consumer.consumer.close(autocommit=True)
    if hasattr(consumer, 'db_connection') and consumer.db_connection:
        logger.info("PostgreSQL 연결을 종료합니다")
        consumer.db_connection.close()
    logger.info("모든 리소스가 정상적으로 종료되었습니다")
    sys.exit(0)

class VoteConsumer:
    def __init__(self):
        # 환경 변수에서 설정 가져오기
        kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka-service.cluster.local:9092").split(",")
        redis_host = os.environ.get("REDIS_HOST", "redis-service.cluster.local")
        redis_port = int(os.environ.get("REDIS_PORT", 6379))
        topic = "vote-events"
        
        # PostgreSQL 접속 정보
        self.pg_host = os.environ.get("POSTGRES_HOST", "postgres-service.cluster.local")
        self.pg_port = os.environ.get("POSTGRES_PORT", "5432")
        self.pg_db = os.environ.get("POSTGRES_DB", "votingdb")
        self.pg_user = os.environ.get("POSTGRES_USER", "postgres")
        self.pg_password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        
        logger.info(f"설정: KAFKA={kafka_servers}, REDIS={redis_host}:{redis_port}, POSTGRES={self.pg_host}:{self.pg_port}")
        
        # 호스트명으로 고유 ID 생성
        client_id = f"vote-consumer-{os.getenv('HOSTNAME', 'unknown')}-{int(time.time())}"
        logger.info(f"고유 클라이언트 ID 생성: {client_id}")
        
        # Kafka 컨슈머 설정
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=kafka_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id='vote-processor',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            session_timeout_ms=60000,
            request_timeout_ms=70000,
            client_id=client_id  # 고유 ID 추가
        )
        
        # Redis 클라이언트 설정
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True
        )
        
        # PostgreSQL 연결
        self.db_connection = self._init_db_connection()
        if not self.db_connection:
            logger.critical("초기 PostgreSQL 연결 실패. 컨슈머가 데이터베이스에 저장할 수 없습니다.")
            logger.critical("네트워크 설정, 자격 증명, PostgreSQL 서버 상태를 확인하세요.")
            # 연결 실패해도 계속 진행 (Redis에는 저장 가능)

        logger.info("컨슈머 초기화 완료")
    
    def _init_db_connection(self, max_retries=3, retry_delay=2):
        """PostgreSQL 데이터베이스 연결 초기화 (재시도 로직 포함)"""
        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                logger.info(f"PostgreSQL 연결 시도 ({retries+1}/{max_retries})...")

                conn = psycopg2.connect(
                    host=self.pg_host,
                    port=self.pg_port,
                    dbname="votingdb",
                    user="postgres",
                    password="postgres"
                )

                # Autocommit 설정 (명시적 트랜잭션 관리 용이)
                conn.autocommit = True

                logger.info("PostgreSQL 데이터베이스 연결 성공")

                # 테이블 스키마 확인 및 필요한 경우 수정
                self._check_and_fix_table_schema(conn)

                return conn
            except Exception as e:
                last_error = str(e)
                logger.warning(f"PostgreSQL 연결 실패 ({retries+1}/{max_retries}): {str(e)}")
                retries += 1
                if retries < max_retries:
                    logger.info(f"{retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)

        logger.error(f"PostgreSQL 연결 최종 실패: {last_error}")
        return None
    
    def _check_and_fix_table_schema(self, conn):
        """테이블 스키마를 확인하고 필요한 경우 수정"""
        try:
            cursor = conn.cursor()
            
            # 테이블이 존재하는지 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'votes'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # 테이블이 없으면 생성
                logger.info("votes 테이블이 없습니다. 새로 생성합니다.")
                cursor.execute("""
                    CREATE TABLE votes (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        candidate_id VARCHAR(50) NOT NULL,
                        vote_time TIMESTAMP NOT NULL,
                        message_id VARCHAR(100) NOT NULL,
                        vote_type VARCHAR(20) NOT NULL DEFAULT 'for',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    ALTER TABLE votes ADD CONSTRAINT votes_message_id_key UNIQUE (message_id);
                    CREATE INDEX idx_votes_candidate_id ON votes(candidate_id);
                    CREATE INDEX idx_votes_vote_type ON votes(vote_type);
                """)
                logger.info("votes 테이블 생성 완료")
            else:
                # 컬럼 확인
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'votes';
                """)
                
                columns = [row[0] for row in cursor.fetchall()]
                logger.info(f"votes 테이블의 현재 컬럼: {columns}")
                
                # vote_type 컬럼이 없으면 추가
                if 'vote_type' not in columns:
                    logger.info("vote_type 컬럼이 없습니다. 추가합니다.")
                    cursor.execute("""
                        ALTER TABLE votes ADD COLUMN vote_type VARCHAR(20) NOT NULL DEFAULT 'for';
                        CREATE INDEX IF NOT EXISTS idx_votes_vote_type ON votes(vote_type);
                    """)
                    logger.info("vote_type 컬럼 추가 완료")
                
                # vote_time 컬럼이 없고 timestamp 컬럼이 있으면 이름 변경
                if 'vote_time' not in columns and 'timestamp' in columns:
                    logger.info("timestamp 컬럼을 vote_time으로 변경합니다.")
                    cursor.execute("""
                        ALTER TABLE votes RENAME COLUMN "timestamp" TO vote_time;
                    """)
                    logger.info("컬럼 이름 변경 완료")
                
                # vote_time 컬럼이 없고 timestamp 컬럼도 없으면 추가
                if 'vote_time' not in columns and 'timestamp' not in columns:
                    logger.info("vote_time 컬럼이 없습니다. 추가합니다.")
                    cursor.execute("""
                        ALTER TABLE votes ADD COLUMN vote_time TIMESTAMP NOT NULL DEFAULT NOW();
                    """)
                    logger.info("vote_time 컬럼 추가 완료")
            
            cursor.close()
            logger.info("테이블 스키마 확인 및 수정 완료")
            
        except Exception as e:
            logger.error(f"테이블 스키마 확인/수정 중 오류: {str(e)}")
    
    def save_to_postgres(self, vote_data):
        """투표 데이터를 PostgreSQL에 저장"""
        # 연결이 없거나 닫혀 있으면 재연결
        if not self.db_connection or (hasattr(self.db_connection, 'closed') and self.db_connection.closed):
            logger.warning("PostgreSQL 연결이 없거나 닫혀 있어 재연결 시도...")
            self.db_connection = self._init_db_connection()
            if not self.db_connection:
                logger.error("PostgreSQL 재연결 실패. 저장할 수 없습니다.")
                return False

        try:
            # timestamp 필드가 있으면 vote_time으로 변환
            if 'timestamp' in vote_data and not 'vote_time' in vote_data:
                vote_data['vote_time'] = vote_data['timestamp']

            cursor = self.db_connection.cursor()
            
            # 이미 존재하는지 확인 (중복 저장 방지)
            cursor.execute(
                "SELECT 1 FROM votes WHERE message_id = %s LIMIT 1",
                (vote_data['message_id'],)
            )
            
            if cursor.fetchone():
                logger.warning(f"메시지 ID {vote_data['message_id']}는 이미 저장되어 있습니다.")
                cursor.close()
                return True
                
            # 저장
            cursor.execute(
                """
                INSERT INTO votes (user_id, candidate_id, vote_time, message_id, vote_type)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    vote_data['user_id'],
                    vote_data['candidate_id'],
                    vote_data.get('vote_time', datetime.now().isoformat()),  # timestamp에서 vote_time으로 변경
                    vote_data['message_id'],
                    vote_data.get('vote_type', 'for')
                )
            )
            
            cursor.close()
            logger.info(f"PostgreSQL에 투표 저장 완료: {vote_data['message_id']}")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL 저장 오류: {str(e)}")
            # 연결 재시도
            try:
                if self.db_connection.closed:
                    self.db_connection = self._init_db_connection()
                    if not self.db_connection:
                        logger.error("PostgreSQL 재연결 실패. 저장할 수 없습니다.")
            except:
                pass
            return False
    
    def validate_data_consistency(self):
        """Redis와 PostgreSQL 간의 데이터 정합성 검증"""
        if not self.db_connection:
            logger.error("PostgreSQL 연결이 없어 검증할 수 없습니다.")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # 먼저 테이블이 존재하는지 확인
            cursor.execute("""
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'votes'
);
            """)
            
            table_exists = cursor.fetchone()[0]
            if not table_exists:
                logger.error("votes 테이블이 존재하지 않습니다. 데이터베이스 초기화가 필요합니다.")
                return
                
            # 컬럼 확인
            cursor.execute("""
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'votes';
            """)
            
            columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"votes 테이블의 컬럼: {columns}")
            
            if 'vote_type' not in columns:
                logger.error("vote_type 컬럼이 votes 테이블에 존재하지 않습니다.")
                return
            
            # PostgreSQL에서 후보별 투표 수 계산 - 컬럼 이름을 따옴표로 감싸서 새로 작성
            cursor.execute("""
SELECT "candidate_id", "vote_type", COUNT(*) as count
FROM votes
GROUP BY "candidate_id", "vote_type";
            """)
            
            pg_results = {f"{row[0]}:{row[1]}": row[2] for row in cursor.fetchall()}
            
            # Redis에서 후보별 투표 수 가져오기
            redis_keys = self.redis_client.keys("vote_result:*")
            redis_results = {}
            
            for key in redis_keys:
                value = self.redis_client.get(key)
                if value:
                    redis_results[key.replace("vote_result:", "")] = int(value)
            
            # 결과 비교 및 로깅
            all_keys = set(pg_results.keys()).union(set(redis_results.keys()))
            
            logger.info("===== 데이터 정합성 검증 =====")
            for key in all_keys:
                pg_count = pg_results.get(key, 0)
                redis_count = redis_results.get(key, 0)
                diff = redis_count - pg_count
                
                status = "✅ 일치" if diff == 0 else f"⚠️ 불일치 (차이: {diff})"
                logger.info(f"{key}: PostgreSQL={pg_count}, Redis={redis_count} - {status}")
                
            cursor.close()
        except Exception as e:
            logger.error(f"데이터 정합성 검증 오류: {str(e)}")
    
    def process_message(self, message):
        """메시지 처리 로직"""
        try:
            vote_data = message.value
            candidate_id = vote_data['candidate_id']
            vote_type = vote_data.get('vote_type', 'for')  # 기본값은 'for'
            message_id = vote_data.get('message_id', 'unknown')
            
            # timestamp 필드가 있으면 vote_time으로 변환
            if 'timestamp' in vote_data and not 'vote_time' in vote_data:
                vote_data['vote_time'] = vote_data['timestamp']

            # Redis에 투표 수 증가
            key = f"vote_result:{candidate_id}:{vote_type}"
            result = self.redis_client.incr(key)
            
            # PostgreSQL 연결 확인 및 재시도
            if not self.db_connection or (hasattr(self.db_connection, 'closed') and self.db_connection.closed):
                logger.warning("PostgreSQL 연결 상태 확인 중 재연결 시도...")
                self.db_connection = self._init_db_connection()

            # PostgreSQL에 저장
            saved = self.save_to_postgres(vote_data)
            if saved:
                logger.info(f"처리된 투표 ID: {message_id} - 후보: {candidate_id}, 타입: {vote_type}, 현재 수: {result}, PostgreSQL 저장: 성공")
            else:
                logger.warning(f"처리된 투표 ID: {message_id} - 후보: {candidate_id}, 타입: {vote_type}, 현재 수: {result}, PostgreSQL 저장: 실패")
            
            return True
        except KeyError as ke:
            logger.error(f"메시지 형식 오류 (필수 필드 누락): {str(ke)}")
            return False
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
            return False
            
    def start_consuming(self):
        logger.info("메시지 소비 시작...")
        last_validation_time = time.time()
        
        try:
            for message in self.consumer:
                if self.process_message(message):
                    self.consumer.commit()
                
                # 5분마다 데이터 정합성 검증
                current_time = time.time()
                if current_time - last_validation_time > 300:  # 300초 = 5분
                    self.validate_data_consistency()
                    last_validation_time = current_time
                    
        except Exception as e:
            logger.error(f"소비자 루프 내 오류: {str(e)}")
        finally:
            if self.db_connection:
                self.db_connection.close()
            self.consumer.close()
            logger.info("투표 소비자 종료됨.")

if __name__ == "__main__":
    try:
        # SIGTERM 시그널 핸들러 등록
        consumer = None  # 전역 변수로 초기화
        signal.signal(signal.SIGTERM, handle_sigterm)
        
        consumer = VoteConsumer()
        logger.info("SIGTERM 핸들러 등록 완료 - 안전한 종료 준비됨")
        consumer.start_consuming()
    except Exception as e:
        logger.critical(f"치명적 오류로 프로그램 종료: {str(e)}")
        sys.exit(1) 