from typing import TypedDict, Literal, Optional, Dict, List, Annotated
import operator
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    source: Literal["audio", "ocr"]
    timestamp: Optional[str] = None

class ComplianceIssue(BaseModel):
    category: List[Evidence] = Field(default_factory=list,description="Whether it is audio or OCR text with corresponding timestamp when that violation happened if anything has happened otherwise keep it empty")
    description: str = Field(...,description="The description of the issue with references to relevant rules flouted in the report and possible repercussions and recommendation. If no violation just return no violation found.")
    severity: Optional[Literal["low", "medium", "high"]]= Field(default=None,description="The severity of the issue, 'low', 'medium', or 'high' based on the repercussions and impact on brand image. If there is no violation dont give anything")
    status: Literal["FAIL", "PASS", "unknown"] = Field(...,description="Whether the video passes or fails the compliance rules if the entire retrieved report is empty or having very little content return 'unknown' otherwise even the slightest issue should give fail and should be also metioned in overall format.")


class GraphState(TypedDict):
    video_url: Optional[str]
    ingestion_video_path: str
    
    video_metadata: Dict[str, str]
    transcript: Optional[str]
    ocr_text: List[str]

    compliance_results: Annotated[List[ComplianceIssue], operator.add]

    final_result: Literal["FAIL", "PASS", "unknown"]=Field(...,description="The final result of the system based on the compliance results, 'unknown' if no results were found due to an error or failure in judgement.")

    report: str= Field(...,description="The final report created by the system based on the compliance results in markdown format")

    errors: Annotated[List[str], operator.add]