import os
from fastapi import APIRouter, Depends, HTTPException
from app.models.vote import VoteResult
from app.services.redis_service import RedisService
from typing import Dict, Any
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["results"])

# Redis 서비스 초기화
redis_service = RedisService(host="redis-service.cluster.local", port=6379)

@router.get("/results", response_model=VoteResult)
async def get_results():
    """
    Redis에서 캐시된 투표 결과를 가져옴
    """
    try:
        logger.info("투표 결과 요청 받음")
        logger.info(f"Redis 서비스 상태: {redis_service}")
        
        results = redis_service.get_vote_results()
        logger.info(f"투표 결과 성공적으로 가져옴: {results}")
        return VoteResult(results=results)
    except Exception as e:
        logger.error(f"결과 조회 중 오류 발생: {str(e)}")
        logger.exception("상세 오류:")
        raise HTTPException(status_code=500, detail=f"결과 조회 중 오류 발생: {str(e)}") 