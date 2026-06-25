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

def index_video_node(state: VideoAuditState) -> Dict[str, Any]:
    '''
    Downloads the youtube video from the url
    Uploads to the Azure Video indexer
    extracts the insights
    '''

    video_url = state.get("video_url")
    video_id_input = state.get("video_id", "vid_demo")

    logger.info(f"-----[Node:Indexer] Processing : {video_url}")

    local_filename = "temp_audit_video.mp4"
    try:
        vi_service = VideoIndexerService()

        # download
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(
                video_url,
                output_path=local_filename
            )
        else:
            raise Exception(
                "Please provide a valid YouTube URL for this test."
            )

        # upload
        azure_video_id = vi_service.upload_video(
            local_path,
            video_name=video_id_input
        )

        logger.info(
            f"Upload Success. Azure ID : {azure_video_id}"
        )
        raw_insights = vi_service.wait_for_processing(azure_video_id)

        # extract
        clean_data = vi_service.extract_data(raw_insights)

        logger.info(
            "---[NODE: Indexer] Extraction Complete ----------"
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