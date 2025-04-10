import redis
import os

class RedisService:
    def __init__(self, host=None, port=None, db=0):
        host = host or os.getenv("REDIS_HOST", "redis-service")
        port = int(port or os.getenv("REDIS_PORT", "6379"))
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def get_vote_results(self):
        """투표 결과를 Redis에서 가져옴"""
        # Redis에서 모든 후보의 투표 결과를 가져옴
        keys = self.redis_client.keys("vote_result:*")
        results = {}

        # 먼저 monthly와 biweekly에 대한 for/against 표 초기화
        results["monthly"] = {"for": 0, "against": 0, "total": 0}
        results["biweekly"] = {"for": 0, "against": 0, "total": 0}

        for key in keys:
            key_str = key.decode("utf-8")
            parts = key_str.split(":")
            
            vote_count = int(self.redis_client.get(key))
            
            # vote_result:candidate_id:vote_type 형식 처리
            if len(parts) == 3:
                candidate_id = parts[1]
                vote_type = parts[2]
                
                # None 타입은 for로 처리 (기본값)
                if vote_type == "None":
                    vote_type = "for"
                
                if candidate_id in ["monthly", "biweekly"] and vote_type in ["for", "against"]:
                    results[candidate_id][vote_type] += vote_count
                    results[candidate_id]["total"] += vote_count
            
            # vote_result:candidate_id 형식 처리 (이전 데이터 호환)
            elif len(parts) == 2:
                candidate_id = parts[1]
                if candidate_id in ["monthly", "biweekly"]:
                    results[candidate_id]["for"] += vote_count
                    results[candidate_id]["total"] += vote_count

        return results
