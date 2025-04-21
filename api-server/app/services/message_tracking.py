import json
import logging
import os
import redis
import time
from typing import List, Dict, Optional
from models.vote import MessageStatus

# 로깅 설정
logger = logging.getLogger("MessageTrackingService")

class MessageTrackingService:
    def __init__(self):
        # Redis 연결 정보
        self.redis_host = os.environ.get("REDIS_HOST", "redis")
        self.redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        
        # Redis 연결
        self._connect_to_redis()
    
    def _connect_to_redis(self):
        """Redis에 연결"""
        try:
            logger.info(f"Connecting to Redis at {self.redis_host}:{self.redis_port}")
            self.redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True
            )
            self.redis.ping()  # 연결 확인
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            # 여기서 예외를 다시 발생시키지 않고 로깅만 함
            # 서비스가 시작될 때 Redis가 아직 준비되지 않았을 수 있음
            self.redis = None
    
    def record_message_status(self, status: MessageStatus):
        """메시지 상태 기록"""
        if not self.redis:
            self._connect_to_redis()
            if not self.redis:
                logger.error("Redis connection not available, cannot record message status")
                return False
        
        try:
            # 메시지 ID를 키로 사용하여 타임라인에 상태 추가
            timeline_key = f"message:{status.message_id}:timeline"
            
            # 상태 데이터 준비
            status_data = {
                "status": status.status,
                "timestamp": status.timestamp.isoformat(),
                "details": json.dumps(status.details) if status.details else "{}"
            }
            
            # 타임라인에 상태 추가 (시간순으로 정렬)
            score = time.time()
            self.redis.zadd(timeline_key, {json.dumps(status_data): score})
            
            # 메시지 ID를 활성 메시지 집합에 추가
            self.redis.sadd("active_messages", status.message_id)
            
            # 메시지 상태에 따라 처리
            if status.status == "processed":
                # 처리 완료된 메시지는 활성 목록에서 제거
                self.redis.srem("active_messages", status.message_id)
                
                # 메시지 타임라인에 만료 시간 설정 (예: 1일)
                self.redis.expire(timeline_key, 86400)
            
            logger.debug(f"Recorded message status: {status.message_id} -> {status.status}")
            return True
        except Exception as e:
            logger.error(f"Error recording message status: {str(e)}")
            return False
    
    def get_message_timeline(self, message_id: str) -> List[Dict]:
        """특정 메시지의 타임라인 조회"""
        if not self.redis:
            self._connect_to_redis()
            if not self.redis:
                logger.error("Redis connection not available, cannot get message timeline")
                return []
        
        try:
            timeline_key = f"message:{message_id}:timeline"
            
            # 시간순으로 정렬된 상태 목록 조회
            status_list = self.redis.zrange(timeline_key, 0, -1)
            
            # JSON 문자열을 객체로 변환
            timeline = [json.loads(status) for status in status_list]
            
            return timeline
        except Exception as e:
            logger.error(f"Error getting message timeline: {str(e)}")
            return []
    
    def get_unprocessed_messages(self) -> List[str]:
        """처리되지 않은 메시지 목록 조회"""
        if not self.redis:
            self._connect_to_redis()
            if not self.redis:
                logger.error("Redis connection not available, cannot get unprocessed messages")
                return []
        
        try:
            # 활성 메시지 집합에서 모든 메시지 ID 조회
            return list(self.redis.smembers("active_messages"))
        except Exception as e:
            logger.error(f"Error getting unprocessed messages: {str(e)}")
            return []
    
    def get_processing_stats(self) -> Dict:
        """메시지 처리 통계 조회"""
        if not self.redis:
            self._connect_to_redis()
            if not self.redis:
                logger.error("Redis connection not available, cannot get processing stats")
                return {"error": "Redis connection not available"}
        
        try:
            # 기본 통계 정보
            stats = {
                "unprocessed_count": self.redis.scard("active_messages"),
                "processed_today": 0,
                "error_count": 0
            }
            
            # 오늘 처리된 메시지 수 (예시 - 실제로는 다른 방식으로 구현할 수 있음)
            today_key = f"stats:processed:{time.strftime('%Y-%m-%d')}"
            processed_today = self.redis.get(today_key)
            if processed_today:
                stats["processed_today"] = int(processed_today)
            
            # 오류 수
            error_key = "stats:errors:count"
            error_count = self.redis.get(error_key)
            if error_count:
                stats["error_count"] = int(error_count)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {"error": str(e)} 