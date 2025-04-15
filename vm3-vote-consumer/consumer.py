import json
import logging
from kafka import KafkaConsumer
import redis
import os
import time
import sys
from datetime import datetime

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

class VoteConsumer:
    def __init__(self):
        # 환경 변수에서 설정 가져오기
        kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "172.16.1.17:9092").split(",")
        redis_host = os.environ.get("REDIS_HOST", "172.16.1.17")
        redis_port = int(os.environ.get("REDIS_PORT", 6379))
        topic = "vote-events"
        
        logger.info(f"설정: KAFKA={kafka_servers}, REDIS={redis_host}:{redis_port}")
        
        # Kafka 컨슈머 설정
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=kafka_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id='vote-processor',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            session_timeout_ms=60000,
            request_timeout_ms=70000
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
        
        logger.info("컨슈머 초기화 완료")
    
    def process_message(self, message):
        try:
            vote_data = message.value
            candidate_id = vote_data['candidate_id']
            vote_type = vote_data.get('vote_type', 'for')  # 기본값은 'for'
            message_id = vote_data.get('message_id', 'unknown')
            
            # Redis에 투표 수 증가
            key = f"vote_result:{candidate_id}:{vote_type}"
            result = self.redis_client.incr(key)
            
            logger.info(f"처리된 투표 ID: {message_id} - 후보: {candidate_id}, 타입: {vote_type}, 현재 수: {result}")
            return True
        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
            return False
            
    def start_consuming(self):
        logger.info("메시지 소비 시작...")
        try:
            for message in self.consumer:
                if self.process_message(message):
                    self.consumer.commit()
        except Exception as e:
            logger.error(f"소비자 루프 내 오류: {str(e)}")
        finally:
            self.consumer.close()
            logger.info("투표 소비자 종료됨.")

if __name__ == "__main__":
    try:
        consumer = VoteConsumer()
        consumer.start_consuming()
    except Exception as e:
        logger.critical(f"치명적 오류로 프로그램 종료: {str(e)}")
        sys.exit(1) 