#!/usr/bin/env python3
"""
투표 이벤트 처리를 위한 Kafka 소비자
- Kafka에서 투표 이벤트를 소비
- Redis에 실시간 집계 결과 저장
- PostgreSQL에 영구 저장
"""

import json
import logging
import os
import sys
import time
import signal
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

# Kafka 
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

# Redis
import redis

# PostgreSQL
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/consumer.log')
    ]
)
logger = logging.getLogger("vote-consumer")

# 환경 변수
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "vote-events")
KAFKA_GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "vote-consumer-group")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "votingdb")

# 상태 추적을 위한 글로벌 변수
running = True

def init_db() -> None:
    """PostgreSQL 데이터베이스 테이블 초기화"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB
        )
        
        with conn.cursor() as cur:
            # 투표 테이블 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    id SERIAL PRIMARY KEY,
                    message_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    vote_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 집계 결과 테이블 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vote_results (
                    candidate_id TEXT NOT NULL,
                    vote_type TEXT NOT NULL,
                    count INT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (candidate_id, vote_type)
                );
            """)
            
            # 메시지 처리 상태 테이블 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS message_status (
                    message_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    details JSONB,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.commit()
            logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        if conn:
            conn.close()

def connect_to_kafka() -> Optional[KafkaConsumer]:
    """Kafka 소비자 연결 - 재시도 로직 포함"""
    max_retries = 10
    retry_interval = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS} (attempt {attempt+1}/{max_retries})")
            
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                max_poll_interval_ms=300000,  # 5분
                session_timeout_ms=30000,     # 30초
                heartbeat_interval_ms=10000   # 10초
            )
            
            logger.info("Successfully connected to Kafka")
            return consumer
        except NoBrokersAvailable:
            logger.warning(f"No brokers available, retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(retry_interval)
    
    logger.error("Failed to connect to Kafka after multiple attempts")
    return None

def connect_to_redis() -> Optional[redis.Redis]:
    """Redis 연결"""
    try:
        logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
            decode_responses=True
        )
        redis_client.ping()  # 연결 확인
        logger.info("Successfully connected to Redis")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def connect_to_postgres() -> Optional[psycopg2.extensions.connection]:
    """PostgreSQL 연결"""
    try:
        logger.info(f"Connecting to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}")
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB
        )
        logger.info("Successfully connected to PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def process_vote_message(message: Dict[str, Any], redis_client: redis.Redis, pg_conn: psycopg2.extensions.connection) -> bool:
    """투표 메시지 처리"""
    try:
        # 메시지 구조 검증
        required_fields = ['message_id', 'user_id', 'candidate_id', 'vote_type', 'timestamp']
        if not all(field in message for field in required_fields):
            logger.error(f"Invalid message format: {message}")
            return False
        
        message_id = message['message_id']
        user_id = message['user_id']
        candidate_id = message['candidate_id']
        vote_type = message['vote_type']
        timestamp = datetime.fromisoformat(message['timestamp'])
        
        logger.info(f"Processing vote: message_id={message_id}, user_id={user_id}, candidate_id={candidate_id}, vote_type={vote_type}")
        
        # 메시지 상태 업데이트 (Redis)
        timeline_key = f"message:{message_id}:timeline"
        status_data = {
            "status": "consumed",
            "timestamp": datetime.now().isoformat(),
            "details": json.dumps({"consumer_id": KAFKA_GROUP_ID})
        }
        score = time.time()
        redis_client.zadd(timeline_key, {json.dumps(status_data): score})
        
        # PostgreSQL에 저장
        with pg_conn.cursor() as cur:
            # 투표 저장
            cur.execute("""
                INSERT INTO votes (message_id, user_id, candidate_id, vote_type, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
                RETURNING id;
            """, (message_id, user_id, candidate_id, vote_type, timestamp))
            
            result = cur.fetchone()
            if result:
                # 새 투표가 추가된 경우에만 카운터 증가
                vote_id = result[0]
                logger.info(f"Vote saved to database with ID {vote_id}")
                
                # 투표 유형별 카운터 업데이트 (Redis)
                vote_key = f"vote:{candidate_id}:{vote_type}"
                redis_client.incr(vote_key)
                
                # 결과 테이블 업데이트 (PostgreSQL)
                cur.execute("""
                    INSERT INTO vote_results (candidate_id, vote_type, count, last_updated)
                    VALUES (%s, %s, 1, NOW())
                    ON CONFLICT (candidate_id, vote_type) DO UPDATE
                    SET count = vote_results.count + 1,
                        last_updated = NOW();
                """, (candidate_id, vote_type))
            else:
                logger.info(f"Vote already processed (duplicate message_id: {message_id})")
            
            # 메시지 상태 업데이트 (PostgreSQL)
            cur.execute("""
                INSERT INTO message_status (message_id, status, details, timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (message_id) DO UPDATE
                SET status = EXCLUDED.status,
                    details = EXCLUDED.details,
                    timestamp = EXCLUDED.timestamp;
            """, (message_id, "processed", json.dumps({"processor": KAFKA_GROUP_ID}), datetime.now()))
            
            pg_conn.commit()
        
        # 메시지 상태 업데이트 (Redis - 처리 완료)
        status_data = {
            "status": "processed",
            "timestamp": datetime.now().isoformat(),
            "details": json.dumps({"processor": KAFKA_GROUP_ID})
        }
        score = time.time()
        redis_client.zadd(timeline_key, {json.dumps(status_data): score})
        
        # 활성 메시지 목록에서 제거
        redis_client.srem("active_messages", message_id)
        
        return True
    except Exception as e:
        logger.error(f"Error processing vote message: {str(e)}")
        logger.error(traceback.format_exc())
        
        if pg_conn:
            pg_conn.rollback()
        
        # 실패 상태 기록 (Redis)
        try:
            status_data = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "details": json.dumps({"error": str(e)})
            }
            score = time.time()
            redis_client.zadd(f"message:{message['message_id']}:timeline", {json.dumps(status_data): score})
        except:
            pass
        
        return False

def signal_handler(sig, frame):
    """프로세스 종료 시그널 핸들러"""
    global running
    logger.info("Received termination signal, shutting down...")
    running = False

def main():
    """메인 함수"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting vote consumer service")
    
    # 데이터베이스 초기화
    init_db()
    
    while running:
        # Kafka 소비자 연결
        consumer = connect_to_kafka()
        if not consumer:
            logger.error("Failed to connect to Kafka, retrying in 30 seconds...")
            time.sleep(30)
            continue
        
        # Redis 연결
        redis_client = connect_to_redis()
        if not redis_client:
            logger.error("Failed to connect to Redis, retrying in 30 seconds...")
            consumer.close()
            time.sleep(30)
            continue
        
        # PostgreSQL 연결
        pg_conn = connect_to_postgres()
        if not pg_conn:
            logger.error("Failed to connect to PostgreSQL, retrying in 30 seconds...")
            consumer.close()
            time.sleep(30)
            continue
        
        try:
            logger.info(f"Starting to consume messages from topic {KAFKA_TOPIC}")
            
            # 메시지 소비 루프
            for message in consumer:
                if not running:
                    break
                
                try:
                    # 메시지 처리
                    vote_data = message.value
                    logger.debug(f"Received message: {vote_data}")
                    
                    success = process_vote_message(vote_data, redis_client, pg_conn)
                    
                    if success:
                        # 오프셋 커밋 (메시지 처리 확인)
                        consumer.commit()
                        logger.debug(f"Committed offset for partition {message.partition}, offset {message.offset}")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error in consumer loop: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # 리소스 정리
            try:
                if consumer:
                    consumer.close()
            except:
                pass
            
            try:
                if pg_conn:
                    pg_conn.close()
            except:
                pass
            
            if running:
                logger.info("Consumer loop exited, restarting in 10 seconds...")
                time.sleep(10)
    
    logger.info("Vote consumer service shutdown complete")

if __name__ == "__main__":
    main() 