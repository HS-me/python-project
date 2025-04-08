from fastapi import APIRouter, Depends, HTTPException
from app.models.vote import Vote
from app.services.kafka_producer import KafkaVoteProducer

router = APIRouter(prefix="/api", tags=["votes"])

# Kafka producer ?몄뒪?댁뒪
kafka_producer = KafkaVoteProducer()

@router.post("/vote")
async def submit_vote(vote: Vote):
    """
    ?ы몴瑜??쒖텧?섍퀬 Kafka??硫붿떆吏瑜?蹂대깂
    """
    try:
        # Kafka???ы몴 ?곗씠???꾩넚
        future = kafka_producer.send_vote(vote)
        # 硫붿떆吏 ?꾩넚 ?뺤씤 (?좏깮??
        future.get(timeout=10)
        return {"status": "success", "message": "?ы몴媛 ?깃났?곸쑝濡?泥섎━?섏뿀?듬땲??"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"?ы몴 泥섎━ 以??ㅻ쪟 諛쒖깮: {str(e)}") 
