#!/usr/bin/env python3
import json
import logging
import time
import datetime
import psycopg2
import redis
from kafka import KafkaConsumer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정 변수
KAFKA_BOOTSTRAP_SERVERS = ['172.16.1.17:9092']  # VM2의 Kafka 서버 주소
KAFKA_TOPIC = 'vote-events'
KAFKA_GROUP_ID = 'vote-consumer-group'

# PostgreSQL 연결 정보
DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'votingdb'
DB_USER = 'voteuser'
DB_PASSWORD = 'votepass'

# Redis 연결 정보
REDIS_HOST = '172.16.1.17'  # VM2의 Redis 주소
REDIS_PORT = 6379
REDIS_DB = 0

class VoteConsumer:
    def __init__(self):
        # Kafka Consumer 초기화
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # PostgreSQL 연결
        self.db_conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        self.db_cursor = self.db_conn.cursor()
        
        # Redis 연결
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB
        )
        
        logger.info("투표 소비자가 초기화 되었습니다.")
    
    def store_vote_in_db(self, vote_data):
        """PostgreSQL에 투표 데이터 저장"""
        try:
            # 타임스탬프 문자열을 datetime으로 변환
            timestamp = datetime.datetime.fromisoformat(vote_data['timestamp'])
            
            # SQL 쿼리 실행
            self.db_cursor.execute(
                "INSERT INTO votes (user_id, candidate_id, timestamp) VALUES (%s, %s, %s)",
                (vote_data['user_id'], vote_data['candidate_id'], timestamp)
            )
            self.db_conn.commit()
            logger.info(f"투표가 데이터베이스에 저장되었습니다: {vote_data}")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류 발생: {str(e)}")
            self.db_conn.rollback()
            return False
    
    def update_redis_count(self, candidate_id):
        """Redis에서 후보자의 득표수 증가"""
        try:
            # 후보자의 득표수를 1 증가
            key = f"vote_result:{candidate_id}"
            self.redis_client.incr(key)
            logger.info(f"Redis에서 후보자 {candidate_id}의 득표수가 증가했습니다.")
            return True
        except Exception as e:
            logger.error(f"Redis 업데이트 중 오류 발생: {str(e)}")
            return False
    
    def process_message(self, message):
        """메시지 처리"""
        try:
            vote_data = message.value
            logger.info(f"메시지 수신: {vote_data}")
            
            # PostgreSQL에 투표 저장
            db_success = self.store_vote_in_db(vote_data)
            
            # Redis 카운터 업데이트
            if db_success:
                redis_success = self.update_redis_count(vote_data['candidate_id'])
                if redis_success:
                    logger.info("투표가 성공적으로 처리되었습니다.")
                else:
                    logger.warning("Redis 업데이트는 실패했지만 DB에는 저장되었습니다.")
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
    
    def run(self):
        """Consumer 실행"""
        try:
            logger.info("Kafka Consumer가 메시지 수신을 시작합니다...")
            for message in self.consumer:
                self.process_message(message)
        except KeyboardInterrupt:
            logger.info("Consumer가 중지되었습니다.")
        finally:
            # 리소스 정리
            if self.db_conn:
                self.db_cursor.close()
                self.db_conn.close()
            if hasattr(self, 'consumer') and self.consumer:
                self.consumer.close()

if __name__ == "__main__":
    consumer = VoteConsumer()
    consumer.run() 