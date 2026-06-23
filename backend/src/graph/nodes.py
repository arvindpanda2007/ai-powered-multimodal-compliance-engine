import json
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List

from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import AzureSearch

from backend.src.graph.state import GraphState, ComplianceIssue
from backend.src.services.video_indexer import VideoIndexerService

logger = logging.getLogger("compliance-engine")
logging.basicConfig(level=logging.INFO)

load_dotenv()

