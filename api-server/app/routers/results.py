from fastapi import APIRouter, Depends, HTTPException
from app.models.vote import VoteResult
from app.services.redis_service import RedisService
import logging
import redis
import os
import json

router = APIRouter(prefix="/api", tags=["results"])

# 로깅 설정
logger = logging.getLogger("results_router")

# Redis 서비스 인스턴스 생성
redis_service = RedisService()

@router.get("/results")
async def get_results():
    """
    투표 결과를 조회
    """
    try:
        # Redis 서비스를 통해 현재 투표 결과 가져오기
        results = redis_service.get_vote_results()
        
        return {"results": results}
    except Exception as e:
        logger.error(f"투표 결과 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"투표 결과 조회 중 오류 발생: {str(e)}")

@router.get("/results/raw")
async def get_raw_results():
    """
    가공되지 않은 원시 투표 데이터 조회
    """
    try:
        # Redis 클라이언트 가져오기
        redis_client = redis_service.get_client()
        
        # Redis의 모든 투표 관련 키 조회
        all_keys = redis_client.keys("vote:*")
        raw_results = {}
        
        for key in all_keys:
            value = redis_client.get(key)
            raw_results[key] = value
        
        return raw_results
    except Exception as e:
        logger.error(f"원시 투표 결과 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"원시 투표 결과 조회 중 오류 발생: {str(e)}") 