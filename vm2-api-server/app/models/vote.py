from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import datetime
import uuid

class Vote(BaseModel):
    user_id: str
    candidate_id: str
    vote_type: str = "for"  # 기본값은 'for'(찬성)
    timestamp: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class VoteResult(BaseModel):
    results: Dict[str, Dict[str, int]]

class MessageStatus(BaseModel):
    message_id: str
    status: str  # 'produced', 'consumed', 'processed'
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    details: Optional[Dict] = None
