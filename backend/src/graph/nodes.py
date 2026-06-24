import json
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import AzureSearch
import yt_dlp
from pathlib import Path
from urllib.parse import urlparse

from backend.src.graph.state import GraphState, ComplianceIssue
from backend.src.services.video_indexer import VideoIndexerService
import os
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger("compliance-engine")
logging.basicConfig(level=logging.INFO)

load_dotenv()

def is_youtube_url(url: str) -> bool:
    if not url:
        return False

    try:
        parsed = urlparse(url)

        return parsed.netloc.lower() in {
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "www.youtu.be",
        }

    except Exception:
        return False


def is_valid_mp4(path: str) -> bool:
    file_path = Path(path)

    return (
        file_path.exists()
        and file_path.is_file()
        and file_path.suffix.lower() == ".mp4"
    )

def download_youtube_video(url: str) -> str:
    """
    Downloads a YouTube video as MP4 and returns the local path.
    """

    if not is_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    Path("downloads").mkdir(exist_ok=True)

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": "downloads/temp_file.%(ext)s",
        "quiet": True,
    }

    logger.info(f"Downloading video from: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        video_path = ydl.prepare_filename(info)

        video_path = str(Path(video_path).with_suffix(".mp4"))

        logger.info(
            f"Downloaded video: {info['title']} -> {video_path}"
        )

        return video_path

def VideoIndexerNode(state: GraphState):

    """
    Handles both:
    1. YouTube URLs
    2. Uploaded MP4 files

    converts argument to MP4 and uploads to Azure Video Indexer and returns clean data
    """
    try:
        url = state.get("video_url")
        video_path = state.get("ingestion_video_path")

        # YouTube workflow
        if url:

            video_path = download_youtube_video(url)

            if not is_valid_mp4(video_path):
                raise ValueError(
                    f"Downloaded file is not a valid MP4: {video_path}"
                )

        # Uploaded file workflow
        elif video_path:

            if is_youtube_url(video_path):
                raise ValueError(
                    "YouTube URL provided inside ingestion_video_path"
                )

            if not is_valid_mp4(video_path):
                raise ValueError(
                    f"Expected an existing MP4 file: {video_path}"
                )

        # No input
        else:
            raise ValueError(
                "Either video_url or ingestion_video_path must be provided."
            )

        logger.info(
            f"Video ready for Azure Video Indexer: {video_path}"
        )

        vis = VideoIndexerService()

        azure_video_id = vis.upload_video(video_path)

        logger.info(
            f"Upload Successful--- Azure Video Indexer ID: {azure_video_id}"
        )

        raw_insights = vis.wait_for_processing(
            azure_video_id
        )

        clean_data = vis.extract_insights(
            raw_insights
        )

        logger.info(
            "---[NODE: INDEXER]----Extraction Complete----"
        )

        return clean_data

    except Exception as e:

        logger.error(
            f"Error in VideoIndexerNode: {str(e)}"
        )

        return {
            "errors": [str(e)],
            "final_result": "unknown",
            "transcript": None,
            "ocr_text": [],
        }

def AuditContentNode(state: GraphState):
    '''Uses existing knowledge base and GPT-4o to audit Video and audio content'''
    try:
        logger.info(
            "---[NODE: AUDITOR]----Querying Knowledge Base and LLM----"
        )

        transcript = state.get("transcript", "")
        ocr_text = state.get("ocr_text", [])

        if not transcript and not ocr_text:
            return {
                "errors": ["No transcript or OCR text found"],
                "final_result": "FAIL",
            }

        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0
        )

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"
        )

        vector_store = AzureSearch(
            azure_search_endpoint=os.getenv(
                "AZURE_SEARCH_ENDPOINT"
            ),
            azure_search_key=os.getenv(
                "AZURE_SEARCH_API_KEY"
            ),
            index_name=os.getenv(
                "AZURE_SEARCH_INDEX_NAME"
            ),
            embedding_function=embeddings.embed_query,
        )
        
        query_text = f"{transcript}{' '.join(ocr_text)}"

        docs = vector_store.similarity_search(
            query_text,
            k=7
        )

        retrieved_rules = "\n\n".join(
    f"Rule ID: {doc.metadata.get('rule_id')}\n"
    f"{doc.page_content}"
    for doc in docs
)

        logger.info(
            f"Retrieved {len(docs)} compliance rules"
        )

        prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a senior brand compliance auditor.

OFFICIAL REGULATORY RULES:
{retrieved_rules}

INSTRUCTIONS:
ONLY flag violations that are directly supported by the retrieved regulatory rules. Do not infer violations from general knowledge.

1. Analyze both transcript and OCR text and assign each violation with appropriate timestamp.
2. Identify all compliance violations.
3. Explain why each violation occurred.
4. Assign severity.
5. Provide evidence timestamps.
"""
    ),
    (
        "human",
        """
VIDEO_METADATA:
{video_metadata}

TRANSCRIPT:
{transcript}

OCR_TEXT:
{ocr_text}
"""
    )
])

        logger.info("---[NODE: AUDITOR]----Prepared prompts ... Initiating LLM Query----")
        
        structured_llm = llm.with_structured_output(
            ComplianceIssue
        )

        chain = prompt | structured_llm

        result = chain.invoke({
            "retrieved_rules": retrieved_rules,
            "video_metadata": state.get("video_metadata", {}),
            "transcript": transcript,
            "ocr_text": ocr_text,
        })

        prompt = f"generate a concise report based on this result {result} from a video compliance report in a markdown format"
        report = llm.invoke(prompt).content

        return {
    "compliance_results": [result],
    "final_result": result.status,
    "report": report
}
        

    except Exception as e:

        logger.error(
            f"Error in AuditContentNode: {str(e)}"
        )

        return {
            "errors": [str(e)],
            "final_result": "unknown",
        }
        




    
