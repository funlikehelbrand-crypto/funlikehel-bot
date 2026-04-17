"""
Obsługa YouTube — upload filmów, odpowiadanie na komentarze.
"""

import logging
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from claude_agent import get_reply
from google_auth import get_credentials

logger = logging.getLogger(__name__)


def get_youtube_service():
    return build("youtube", "v3", credentials=get_credentials())


# ---------------------------------------------------------------------------
# Upload filmów
# ---------------------------------------------------------------------------

def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: list[str] = None,
    category_id: str = "17",   # 17 = Sport
    privacy: str = "public",
) -> dict:
    """
    Uploaduje film na YouTube.
    privacy: 'public' | 'unlisted' | 'private'
    """
    service = get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or ["kitesurfing", "windsurfing", "funlikehel", "hel", "sporty wodne"],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    media = MediaFileUpload(file_path, resumable=True)

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("Upload: %d%%", int(status.progress() * 100))

    logger.info("Film wgrany: https://youtube.com/watch?v=%s", response["id"])
    return response


# ---------------------------------------------------------------------------
# Komentarze
# ---------------------------------------------------------------------------

def get_unread_comments(video_id: str = None, max_results: int = 20) -> list[dict]:
    """
    Pobiera komentarze bez odpowiedzi z kanału (lub konkretnego filmu).
    """
    service = get_youtube_service()
    params = {
        "part": "snippet",
        "maxResults": max_results,
        "moderationStatus": "published",
        "order": "time",
    }
    if video_id:
        params["videoId"] = video_id
    else:
        params["allThreadsRelatedToChannelId"] = _get_channel_id(service)

    result = service.commentThreads().list(**params).execute()
    items = result.get("items", [])

    # Zwracamy tylko wątki bez odpowiedzi
    return [
        {
            "thread_id": item["id"],
            "video_id": item["snippet"]["videoId"],
            "author": item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
            "text": item["snippet"]["topLevelComment"]["snippet"]["textOriginal"],
            "reply_count": item["snippet"]["totalReplyCount"],
        }
        for item in items
        if item["snippet"]["totalReplyCount"] == 0
    ]


def reply_to_comment(parent_id: str, text: str) -> dict:
    """Odpowiada na komentarz pod filmem."""
    service = get_youtube_service()
    response = service.comments().insert(
        part="snippet",
        body={
            "snippet": {
                "parentId": parent_id,
                "textOriginal": text,
            }
        },
    ).execute()
    return response


def _get_channel_id(service) -> str:
    """Pobiera ID kanału zalogowanego użytkownika."""
    result = service.channels().list(part="id", mine=True).execute()
    return result["items"][0]["id"]


# ---------------------------------------------------------------------------
# Automatyczna obsługa komentarzy przez agenta
# ---------------------------------------------------------------------------

def process_youtube_comments(video_id: str = None):
    """
    Pobiera komentarze bez odpowiedzi i odpowiada przez agenta FunLikeHel.
    """
    comments = get_unread_comments(video_id=video_id)
    if not comments:
        logger.info("Brak nowych komentarzy na YouTube.")
        return

    for comment in comments:
        try:
            logger.info("Komentarz od %s: %s", comment["author"], comment["text"])
            prompt = f"Komentarz pod filmem na YouTube od {comment['author']}:\n{comment['text']}"
            reply = get_reply(prompt, sender_id=comment["author"], channel="youtube")
            reply_to_comment(comment["thread_id"], reply)
            logger.info("Odpowiedź wysłana na YouTube.")
        except Exception as e:
            logger.error("Błąd przy komentarzu YouTube: %s", e)
