from fastapi import APIRouter, Depends, HTTPException
from app.models.vote import Vote, MessageStatus
from app.services.kafka_producer import KafkaVoteProducer
from app.services.message_tracking import MessageTrackingService
from typing import Dict, List, Optional
import logging

router = APIRouter(prefix="/api", tags=["votes"])

# 로깅 설정
logger = logging.getLogger("votes_router")

# 인스턴스 생성
kafka_producer = KafkaVoteProducer()
message_tracker = MessageTrackingService()

@router.post("/vote")
async def submit_vote(vote: Vote):
    """
    투표를 제출하고 Kafka로 메시지를 보냄
    """
    try:
        # Kafka로 투표 데이터 전송
        future = kafka_producer.send_vote(vote)
        # 메시지 전송 확인 (선택적)
        future.get(timeout=10)
        return {"status": "success", "message": "투표가 성공적으로 처리되었습니다", "message_id": vote.message_id}
    except Exception as e:
        logger.error(f"투표 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"투표 처리 중 오류 발생: {str(e)}")

@router.get("/message/{message_id}")
async def get_message_status(message_id: str):
    """
    특정 메시지의 처리 상태를 조회
    """
    try:
        timeline = message_tracker.get_message_timeline(message_id)
        if not timeline:
            raise HTTPException(status_code=404, detail=f"메시지 ID {message_id}를 찾을 수 없습니다")
        
        return {
            "message_id": message_id,
            "timeline": timeline
        }
    except Exception as e:
        logger.error(f"메시지 상태 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 상태 조회 중 오류 발생: {str(e)}")

@router.get("/messages/unprocessed")
async def get_unprocessed_messages():
    """
    처리되지 않은 메시지 목록 조회
    """
    try:
        unprocessed = message_tracker.get_unprocessed_messages()
        return {
            "count": len(unprocessed),
            "messages": unprocessed
        }
    except Exception as e:
        logger.error(f"미처리 메시지 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"미처리 메시지 조회 중 오류 발생: {str(e)}")

@router.get("/stats")
async def get_message_stats():
    """
    메시지 처리 통계 조회
    """
    try:
        stats = message_tracker.get_processing_stats()
        return stats
    except Exception as e:
        logger.error(f"메시지 통계 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 통계 조회 중 오류 발생: {str(e)}")

@router.post("/validate")
async def validate_consistency():
    """
    Redis와 PostgreSQL 간의 데이터 일관성 검증을 요청
    - VM3 워커에서 제공하는 검증 서비스 호출
    """
    try:
        # 여기서는 간단히 워커에 HTTP 요청을 보내거나 직접 구현할 수도 있습니다
        # 실제 구현은 워커 서비스에 API를 추가하거나 메시지를 보내는 방식으로 해야 합니다
        
        # 임시 응답
        return {
            "status": "pending",
            "message": "데이터 일관성 검증이 요청되었습니다. '/api/validate/results'에서 결과를 확인하세요."
        }
    except Exception as e:
        logger.error(f"데이터 일관성 검증 요청 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 일관성 검증 요청 중 오류 발생: {str(e)}") 