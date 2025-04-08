import logging
import redis
import json
from datetime import datetime
from app.models.vote import MessageStatus
from typing import List, Dict, Optional

class MessageTrackingService:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_db=1):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.logger = logging.getLogger("MessageTrackingService")
    
    def record_message_status(self, status: MessageStatus):
        """메시지 상태를 Redis에 기록합니다."""
        key = f"msg:{status.message_id}:{status.status}"
        value = {
            "message_id": status.message_id,
            "status": status.status,
            "timestamp": status.timestamp.isoformat(),
            "details": status.details or {}
        }
        
        try:
            # 메시지 상태 저장
            self.redis_client.set(key, json.dumps(value))
            
            # 메시지 ID 기준으로 타임라인에 추가
            timeline_key = f"msg_timeline:{status.message_id}"
            self.redis_client.rpush(timeline_key, json.dumps(value))
            
            # 전체 메시지 목록에 추가
            self.redis_client.sadd("all_messages", status.message_id)
            
            self.logger.info(f"Recorded message status: {status.message_id} -> {status.status}")
            return True
        except Exception as e:
            self.logger.error(f"Error recording message status: {str(e)}")
            return False
    
    def get_message_timeline(self, message_id: str) -> List[Dict]:
        """특정 메시지의 전체 상태 타임라인을 조회합니다."""
        timeline_key = f"msg_timeline:{message_id}"
        events = self.redis_client.lrange(timeline_key, 0, -1)
        return [json.loads(event) for event in events]
    
    def get_message_status(self, message_id: str, status_type: Optional[str] = None) -> Optional[Dict]:
        """특정 메시지의 특정 상태를 조회합니다."""
        if status_type:
            key = f"msg:{message_id}:{status_type}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        else:
            # 모든 상태 타임라인 반환
            return self.get_message_timeline(message_id)
    
    def get_unprocessed_messages(self) -> List[str]:
        """생성되었으나 처리되지 않은 메시지 목록을 반환합니다."""
        all_messages = self.redis_client.smembers("all_messages")
        unprocessed = []
        
        for msg_id in all_messages:
            msg_id = msg_id.decode("utf-8")
            # produced는 있지만 processed는 없는 메시지 찾기
            if self.redis_client.exists(f"msg:{msg_id}:produced") and not self.redis_client.exists(f"msg:{msg_id}:processed"):
                unprocessed.append(msg_id)
        
        return unprocessed
    
    def get_processing_stats(self) -> Dict:
        """메시지 처리 통계를 반환합니다."""
        all_count = self.redis_client.scard("all_messages")
        
        produced_keys = self.redis_client.keys("msg:*:produced")
        produced_count = len(produced_keys)
        
        consumed_keys = self.redis_client.keys("msg:*:consumed")
        consumed_count = len(consumed_keys)
        
        processed_keys = self.redis_client.keys("msg:*:processed")
        processed_count = len(processed_keys)
        
        failed_keys = self.redis_client.keys("msg:*:failed")
        failed_count = len(failed_keys)
        
        return {
            "total_messages": all_count,
            "produced": produced_count,
            "consumed": consumed_count,
            "processed": processed_count,
            "failed": failed_count,
            "in_transit": produced_count - processed_count - failed_count
        } 