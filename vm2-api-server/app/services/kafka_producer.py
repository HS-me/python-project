import json
import logging
from kafka import KafkaProducer
from app.models.vote import Vote, MessageStatus
from app.services.message_tracking import MessageTrackingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class KafkaVoteProducer:
    def __init__(self, bootstrap_servers=["localhost:9092"], topic="vote-events"):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        self.topic = topic
        self.logger = logging.getLogger("KafkaVoteProducer")
        self.tracking_service = MessageTrackingService()

    def send_vote(self, vote: Vote):
        # 메시지 데이터 준비
        vote_data = {
            "user_id": vote.user_id,
            "candidate_id": vote.candidate_id,
            "vote_type": vote.vote_type,
            "timestamp": vote.timestamp.isoformat(),
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
