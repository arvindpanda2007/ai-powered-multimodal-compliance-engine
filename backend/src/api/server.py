import uuid
import logging

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)
from backend.src.api.telemetry import setup_telemetry

setup_telemetry()
from backend.src.graph.workflow import app as compliance_graph
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-server")
app = FastAPI(
    title="AI Video Compliance Engine API",
    description="API for auditing video content against the brand compliance rules.",
    version="1.0.0"
)                    

class AuditRequest(BaseModel):
    '''
    Define the expected structure of incoming API requests.
    Example valid request:
    {"video_url":"https://youtu.be/abc123"}

    Invalid: 422 error
    {"video_url":12345}
    '''
    video_url: str

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

@app.post("/audit", response_model=GraphState)

async def audit_video(request: AuditRequest):
    '''
    Main API endpoint that triggers the compliance audit workflow.
    '''
    