from typing import TypedDict, Literal, Optional, Dict, List, Annotated
import operator
from pydantic import BaseModel, Field


class ComplianceIssue(BaseModel):
    category: str
    description: str
    severity: Literal["low", "medium", "high"]
    timestamp: Optional[str] = None


class GraphState(TypedDict):
    video_url: str
    video_id: str

    ingestion_video_path: str
    video_metadata: Dict[str, str]
    transcript: Optional[str]
    ocr_text: List[str]

    compliance_results: Annotated[List[ComplianceIssue], operator.add]

    final_result: Literal["FAIL", "PASS"]

    report: str= Field(...,description="The final report created by the system based on the compliance results in markdown format")

    errors: Annotated[List[str], operator.add]