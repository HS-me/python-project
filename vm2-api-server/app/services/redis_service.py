import redis

class RedisService:
    def __init__(self, host="localhost", port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        
    def get_vote_results(self):
        """?ы몴 寃곌낵瑜?Redis?먯꽌 媛?몄샂"""
        # Redis?먯꽌 紐⑤뱺 ?꾨낫???ы몴 寃곌낵瑜?媛?몄샂
        keys = self.redis_client.keys("vote_result:*")
        results = {}
        
        for key in keys:
            candidate_id = key.decode("utf-8").split(":")[-1]
            vote_count = int(self.redis_client.get(key))
            results[candidate_id] = vote_count
            
        return results 
