from typing import Optional, Dict, Any
from pydantic import BaseModel


class RecordCreateRequest(BaseModel):
    analysis_id: str
    case_id: str
    sample_id: str
    operator_id: str
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy: Optional[float] = None
    gps_mock_suspected: bool = False
    capture_mode: str = "online"   # "online" | "offline"
    officer_assessment: Optional[str] = None  # "positive" | "negative" | "inconclusive"


class VerifyRequest(BaseModel):
    record_id: str
    override_fields: Optional[Dict[str, Any]] = None
    override_signature: Optional[str] = None
