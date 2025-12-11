from youtube_transcript_api import YouTubeTranscriptApi
from settings.logger import Logger
from typing import Optional
logger=Logger.get_logger(__name__)

def ytube_transcript(url: str) -> str:
    try:
        logger.info(f"Fetching transcript for URL: {url}")

        if "v=" in url:
            video_id = url.split("v=")[-1]
        else:
            video_id = url.split("/")[-1]

        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)

        text = " ".join([t["text"] for t in transcript])
        return text

    except Exception as e:
        logger.error(f"Transcript error: {e}")
        return ""


import re

yt_pattern = re.compile(r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+")

def extract_yt_url(text: str) -> Optional[str]:
    match = yt_pattern.search(text)
    if match:
        return match.group(0)
    return None
