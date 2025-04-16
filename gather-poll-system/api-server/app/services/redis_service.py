import redis
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self, host=None, port=None):
        # 인자로 전달된 값 또는 환경 변수에서 Redis 서버 주소 가져오기
        redis_host = host or os.environ.get("REDIS_HOST", "redis")
        redis_port = port or int(os.environ.get("REDIS_PORT", 6379))
        
        logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        
    def get_client(self):
        return self.redis_client

    def get_vote_results(self):
        """투표 결과를 Redis에서 가져옴"""
        # Redis에서 모든 후보의 투표 결과를 가져옴
        keys = self.redis_client.keys("vote:*")
        results = {}

        # 먼저 monthly와 biweekly에 대한 for/against 표 초기화
        results["monthly"] = {"for": 0, "against": 0, "total": 0}
        results["biweekly"] = {"for": 0, "against": 0, "total": 0}

        for key in keys:
            # 키는 이미 문자열 상태임 (decode_responses=True 설정 때문)
            key_str = key  # 추가 디코딩 필요 없음
            parts = key_str.split(":")
            
            vote_count = int(self.redis_client.get(key) or 0)
            
            # vote:candidate_id:vote_type 형식 처리
            if len(parts) == 3:
                candidate_id = parts[1]
                vote_type = parts[2]
                
                # None 타입은 for로 처리 (기본값)
                if vote_type == "None":
                    vote_type = "for"
                
                if candidate_id in ["monthly", "biweekly"] and vote_type in ["for", "against"]:
                    results[candidate_id][vote_type] += vote_count
                    results[candidate_id]["total"] += vote_count
            
            # vote:candidate_id 형식 처리 (이전 데이터 호환)
            elif len(parts) == 2:
                candidate_id = parts[1]
                if candidate_id in ["monthly", "biweekly"]:
                    results[candidate_id]["for"] += vote_count
                    results[candidate_id]["total"] += vote_count

        return results 