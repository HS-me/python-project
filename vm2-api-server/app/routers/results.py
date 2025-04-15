import os
from fastapi import APIRouter, Depends, HTTPException
from app.models.vote import VoteResult
from app.services.redis_service import RedisService
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["results"])

# Redis 서비스 초기화
redis_service = RedisService(host="redis-service.cluster.local", port=6379)

@router.get("/results", response_model=VoteResult)
async def get_results():
    """
    Redis에서 캐시된 투표 결과를 가져옴
    """
    try:
        results = redis_service.get_vote_results()
        return VoteResult(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 조회 중 오류 발생: {str(e)}") 