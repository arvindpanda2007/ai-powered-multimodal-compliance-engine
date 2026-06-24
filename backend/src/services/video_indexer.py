import os
import time
import logging
import requests
import yt_dlp

from azure.identity import DefaultAzureCredential

logger = logging.getLogger("video-indexer")


class VideoIndexerService: