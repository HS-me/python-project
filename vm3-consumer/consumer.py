import json
import logging
import time
import psycopg2
import redis
from kafka import KafkaConsumer
from typing import Dict, Any, List
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VoteConsumer")

class MessageTracker:
    def __init__(self, redis_host="172.16.1.17", redis_port=6379, redis_db=1):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.logger = logging.getLogger("MessageTracker")
    
    def record_status(self, message_id: str, status: str, details: Dict = None):
        """메시지 상태를 Redis에 기록합니다."""
        key = f"msg:{message_id}:{status}"
        value = {
            "message_id": message_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        try:
            # 메시지 상태 저장
            self.redis_client.set(key, json.dumps(value))
            
            # 메시지 ID 기준으로 타임라인에 추가
            timeline_key = f"msg_timeline:{message_id}"
            self.redis_client.rpush(timeline_key, json.dumps(value))
            
            self.logger.info(f"Recorded message status: {message_id} -> {status}")
            return True
        except Exception as e:
            self.logger.error(f"Error recording message status: {str(e)}")
            return False

class VoteConsumer:
    def __init__(self, 
                bootstrap_servers=["172.16.1.17:9092"], 
                topic="vote-events",
                redis_host="172.16.1.17",
                redis_port=6379,
                postgres_host="172.16.1.17",
                postgres_port=5432,
                postgres_db="votes_db",
                postgres_user="postgres",
                postgres_password="postgres"):
        
        # Kafka 컨슈머 설정
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id='vote-processor',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # Redis 연결
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
        
        # PostgreSQL 연결 정보
        self.pg_conn_info = {
            "host": postgres_host,
            "port": postgres_port,
            "dbname": postgres_db,
            "user": postgres_user,
            "password": postgres_password
        }
        
        # 메시지 추적기 초기화
        self.tracker = MessageTracker(redis_host=redis_host, redis_port=redis_port)
        
        # 로거 설정
        self.logger = logging.getLogger("VoteConsumer")
        
    def _get_pg_connection(self):
        """PostgreSQL 데이터베이스 연결을 반환합니다."""
        return psycopg2.connect(**self.pg_conn_info)
    
    def process_vote(self, vote_data: Dict[str, Any]):
        self.logger.info(f"Received vote_data: {vote_data}")
        """투표 데이터를 처리합니다."""
        user_id = vote_data["user_id"]
        vote_type = vote_data.get("vote_type")  # vote_type 키가 없을 수 있음
        # 디버깅을 위해 전체 vote_data 출력\n        self.logger.info(f"Received vote_data: {vote_data}")
        candidate_id = vote_data["candidate_id"]
        timestamp = vote_data["timestamp"]
        message_id = vote_data.get("message_id", "unknown")
        
        self.logger.info(f"Processing vote: {message_id} from user {user_id} for {candidate_id} - vote_type: {vote_type}")
        
        # 메시지 소비 상태 기록
        self.tracker.record_status(
            message_id, 
            "consumed", 
            {"user_id": user_id, "candidate_id": candidate_id}
        )
        
        # PostgreSQL에 투표 데이터 저장
        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO votes (user_id, candidate_id, vote_time, message_id, vote_type) 
                        VALUES (%s, %s, %s, %s, %s)
                        """, 
                        (user_id, candidate_id, timestamp, message_id, vote_type)
                    )
                    conn.commit()
                    
            self.logger.info(f"Vote saved to PostgreSQL: {message_id}")
            
            # Redis에 투표 수 증가
            vote_key = f"vote_result:{candidate_id}:{vote_type}"
            self.redis_client.incr(vote_key)
            
            self.logger.info(f"Vote count updated in Redis: {candidate_id}:{vote_type}")
            
            # 메시지 처리 완료 상태 기록
            self.tracker.record_status(
                message_id, 
                "processed", 
                {"user_id": user_id, "candidate_id": candidate_id}
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error processing vote {message_id}: {str(e)}")
            
            # 메시지 처리 실패 상태 기록
            self.tracker.record_status(
                message_id, 
                "failed", 
                {"error": str(e)}
            )
            
            return False
    
    def run(self):
        """컨슈머를 실행하여 메시지를 소비합니다."""
        self.logger.info("Starting vote consumer...")
        
        try:
            # 메인 컨슈머 루프
            for message in self.consumer:
                vote_data = message.value
                
                try:
                    success = self.process_vote(vote_data)
                    
                    if success:
                        # 오프셋 커밋 (메시지 처리 완료 확인)
                        self.consumer.commit()
                except Exception as e:
                    self.logger.error(f"Error in vote processing loop: {str(e)}")
                    # 여기서 전체 루프를 중단하지 않고 계속 진행
        except KeyboardInterrupt:
            self.logger.info("Shutting down vote consumer...")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
        finally:
            self.consumer.close()
            self.logger.info("Vote consumer shut down.")
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """Redis와 PostgreSQL 간의 데이터 일관성을 검증합니다."""
        self.logger.info("Validating data consistency between Redis and PostgreSQL...")
        
        results = {
            "consistent": True,
            "errors": [],
            "redis_counts": {},
            "postgres_counts": {}
        }
        
        # 1. Redis에서 투표 결과 가져오기
        redis_keys = self.redis_client.keys("vote_result:*")
        for key in redis_keys:
            candidate_id = key.decode("utf-8").split(":")[-1]
            vote_count = int(self.redis_client.get(key))
            results["redis_counts"][candidate_id] = vote_count
        
        # 2. PostgreSQL에서 투표 수 가져오기
        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT candidate_id, COUNT(*) as vote_count 
                        FROM votes 
                        GROUP BY candidate_id
                        """
                    )
                    
                    for row in cursor.fetchall():
                        candidate_id, vote_count = row
                        results["postgres_counts"][candidate_id] = vote_count
                        
                    # 누락된 메시지 확인
                    cursor.execute(
                        """
                        SELECT message_id FROM votes
                        """
                    )
                    processed_messages = set(row[0] for row in cursor.fetchall())
        except Exception as e:
            self.logger.error(f"Error validating data consistency: {str(e)}")
            results["consistent"] = False
            results["errors"].append(str(e))
            return results
        
        # 3. Redis와 PostgreSQL 투표 수 비교
        for candidate_id, redis_count in results["redis_counts"].items():
            pg_count = results["postgres_counts"].get(candidate_id, 0)
            
            if redis_count != pg_count:
                results["consistent"] = False
                results["errors"].append(
                    f"Inconsistent count for {candidate_id}: Redis={redis_count}, PostgreSQL={pg_count}"
                )
        
        # 4. 메시지 추적 정보에서 처리된 것으로 표시된 메시지가 실제로 DB에 있는지 확인
        processed_status_keys = self.tracker.redis_client.keys("msg:*:processed")
        for key in processed_status_keys:
            message_id = key.decode("utf-8").split(":")[1]
            
            if message_id not in processed_messages:
                results["consistent"] = False
                results["errors"].append(
                    f"Message {message_id} marked as processed but not found in database"
                )
        
        return results

# 메인 함수
if __name__ == "__main__":
    consumer = VoteConsumer()
    
    # 데이터 일관성 검증을 주기적으로 실행하는 별도 스레드를 시작할 수 있습니다
    # 여기서는 간단히 컨슈머 실행 전에 검증만 수행
    consistency_results = consumer.validate_data_consistency()
    if not consistency_results["consistent"]:
        logger.warning(f"Data inconsistency detected: {consistency_results['errors']}")
    
    # 컨슈머 실행
    consumer.run() 