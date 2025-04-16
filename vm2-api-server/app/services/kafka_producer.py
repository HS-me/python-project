import json
import logging
import os
from kafka import KafkaProducer
from app.models.vote import Vote, MessageStatus
from app.services.message_tracking import MessageTrackingService
import time
from kafka.errors import NoBrokersAvailable
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=10, initial_backoff=1, max_backoff=30):
    """단순한 재시도 데코레이터 함수"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            backoff_time = initial_backoff
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except NoBrokersAvailable as e:
                    logger.warning(f"Backing off {backoff_time} seconds after {retries+1} tries")
                    time.sleep(backoff_time)
                    retries += 1
                    backoff_time = min(backoff_time * 2, max_backoff)
            
            # 최대 재시도 횟수에 도달하면 예외 발생
            raise NoBrokersAvailable("최대 재시도 횟수에 도달했습니다.")
        return wrapper
    return decorator

class KafkaProducerService:
    def __init__(self):
        self.producer = self._create_producer()
        
    @retry_with_backoff(max_retries=10, initial_backoff=1, max_backoff=30)
    def _create_producer(self):
        # 환경 변수에서 Kafka 서버 주소 가져오기
        bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka-service.cluster.local:9092")
        
        # 문자열로 전달된 경우 리스트로 변환
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = bootstrap_servers.split(",")
            
        logger.info(f"Attempting to connect to Kafka servers: {bootstrap_servers}")
        
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # 모든 복제본이 메시지를 받았는지 확인
            retries=5,   # 실패 시 재시도 횟수
            retry_backoff_ms=1000,  # 재시도 간격
            max_in_flight_requests_per_connection=1,  # 순서 보장
            request_timeout_ms=30000,  # 요청 타임아웃
            connections_max_idle_ms=600000  # 연결 유지 시간
        )

    def send_message(self, topic, message):
        try:
            # 메시지에 타임스탬프 추가
            message['vote_time'] = int(time.time() * 1000)
            
            future = self.producer.send(topic, message)
            # 메시지 전송 결과 확인
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent successfully to topic {topic}, partition {record_metadata.partition}, offset {record_metadata.offset}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {str(e)}")
            return False

    def close(self):
        self.producer.close()

class KafkaVoteProducer:
    def __init__(self, bootstrap_servers=None, topic="vote-events"):
        self.topic = topic
        self.logger = logging.getLogger("KafkaVoteProducer")
        self.tracking_service = MessageTrackingService()
        
        # 환경 변수에서 직접 가져오기
        if bootstrap_servers is None:
            bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka-service.cluster.local:9092")
            self.logger.info(f"Using bootstrap servers from env: {bootstrap_servers}")
        
        self.producer = self._create_producer(bootstrap_servers)

    @retry_with_backoff(max_retries=10, initial_backoff=1, max_backoff=30)
    def _create_producer(self, bootstrap_servers):
        # 문자열로 전달된 경우 리스트로 변환
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = bootstrap_servers.split(",")
        
        self.logger.info(f"Attempting to connect to Kafka servers: {bootstrap_servers}")
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
            retry_backoff_ms=1000,
            request_timeout_ms=30000,
            acks='all'  # 모든 복제본이 메시지를 받았는지 확인
        )

    def send_vote(self, vote: Vote):
        # 메시지 데이터 준비
        vote_data = {
            "user_id": vote.user_id,
            "candidate_id": vote.candidate_id,
            "vote_type": vote.vote_type,
            "vote_time": vote.timestamp.isoformat(),
            "message_id": vote.message_id
        }

        # 메시지 데이터 로깅 추가
        self.logger.info(f"Sending vote data: {vote_data}")

        # 메시지 전송 전 로깅
        self.logger.info(f"Producing message: {vote.message_id} for user {vote.user_id}")

        # 메시지 상태 추적 시작
        self.tracking_service.record_message_status(
            MessageStatus(
                message_id=vote.message_id,
                status="produced",
                details={"user_id": vote.user_id, "topic": self.topic}
            )
        )

        # 메시지 전송
        future = self.producer.send(self.topic, value=vote_data)

        # 메시지 전송 성공 확인 (선택적)
        try:
            record_metadata = future.get(timeout=10)
            self.logger.info(f"Message {vote.message_id} sent to {record_metadata.topic} "
                            f"partition {record_metadata.partition} offset {record_metadata.offset}")

            # 메시지 상태 업데이트
            self.tracking_service.record_message_status(
                MessageStatus(
                    message_id=vote.message_id,
                    status="acknowledged",
                    details={
                        "topic": record_metadata.topic,
                        "partition": record_metadata.partition,
                        "offset": record_metadata.offset
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error sending message {vote.message_id}: {str(e)}")
            self.tracking_service.record_message_status(
                MessageStatus(
                    message_id=vote.message_id,
                    status="failed",
                    details={"error": str(e)}
                )
            )
            raise

        return future
