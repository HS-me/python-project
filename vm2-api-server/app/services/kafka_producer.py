import json
from kafka import KafkaProducer
from app.models.vote import Vote

class KafkaVoteProducer:
    def __init__(self, bootstrap_servers=["localhost:9092"], topic="vote-events"):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        self.topic = topic
        
    def send_vote(self, vote: Vote):
        vote_data = {
            "user_id": vote.user_id,
            "candidate_id": vote.candidate_id,
            "timestamp": vote.timestamp.isoformat()
        }
        future = self.producer.send(self.topic, value=vote_data)
        return future 
