from fastapi import APIRouter, Depends, HTTPException
from models.vote import Vote, MessageStatus
from services.kafka_producer import KafkaVoteProducer       
from services.message_tracking import MessageTrackingService
from typing import Dict, List, Optional
import logging
import traceback

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
        # 디버그 로깅 추가
        logger.info(f"Received vote: {vote.dict()}")
        
        # Kafka로 투표 데이터 전송
        future = kafka_producer.send_vote(vote)
        
        # 디버그 로깅 추가
        logger.info("Waiting for Kafka to confirm receipt")
        
        # 메시지 전송 확인 (선택적)
        record_metadata = future.get(timeout=10)
        
        # 디버그 로깅 추가
        logger.info(f"Vote sent to Kafka: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
        
        return {"status": "success", "message": "투표가 성공적으로 처리되었습니다", "message_id": vote.message_id}
    except Exception as e:
        # 자세한 에러 로깅
        error_msg = f"투표 처리 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

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
    데이터 일관성 검증 요청
    """
    try:
        # 여기에 데이터 일관성 검증 로직 구현
        return {
            "status": "requested",
            "message": "데이터 일관성 검증이 요청되었습니다. '/api/validate/results'에서 결과를 확인하세요."
        }
    except Exception as e:
        logger.error(f"데이터 일관성 검증 요청 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 일관성 검증 요청 중 오류 발생: {str(e)}")      