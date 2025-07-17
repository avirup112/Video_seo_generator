import requests
from urllib.parse import urlparse, parse_qs
import json
import re

def extract_video_id(url):
    """Extracts the video ID from a given YouTube URL."""
    if not url:
        return None

    url = url.strip()
    
    # Add protocol if missing
    if not (url.startswith("http://") or url.startswith("https://")):
        url = 'https://' + url

    # YouTube video URL patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/e\/|youtube\.com\/watch\?.*v=|youtube\.com\/watch\?.*&v=)([^&?#]+)',
        r'youtube\.com\/shorts\/([^&?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        if 'watch' in parsed_url.path:
            query = parse_qs(parsed_url.query)
            if 'v' in query:
                return query['v'][0]
        elif '/shorts/' in parsed_url.path:
            parts = parsed_url.path.split('/')
            idx = parts.index('shorts') if 'shorts' in parts else -1
            if idx != -1 and idx + 1 < len(parts):
                return parts[idx + 1]

    return None

def get_video_platform(url):
    """Detect the platform from URL."""
    if not url:
        return None

    url = url.strip().lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url:
        return "facebook"
    elif "linkedin.com" in url:
        return "linkedin"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "twitter.com" in url or "x.com" in url:
        return "twitter"
    return "unknown"

def get_youtube_metadata(video_id):
    """Fetch YouTube video metadata with fallback."""
    metadata = {
        "title": f"YouTube Video ({video_id})",
        "description": "",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "duration": 300,
        "views": 0,
        "author": "YouTube Creator",
        "platform": "youtube",
        "video_id": video_id,
    }

    try:
        # Method 1: Scrape video page
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            html = response.text

            title = re.search(r'<meta name="og:title" content="([^"]+)"', html)
            author = re.search(r'<link itemprop="name" content="([^"]+)"', html)
            description = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            duration = re.search(r'"lengthSeconds":"(\d+)"', html)
            thumbnail = re.search(r'<meta property="og:image" content="([^"]+)"', html)

            if title: metadata["title"] = title.group(1)
            if author: metadata["author"] = author.group(1)
            if description: metadata["description"] = description.group(1)
            if duration:
                try:
                    metadata["duration"] = int(duration.group(1))
                except ValueError:
                    pass
            if thumbnail: metadata["thumbnail_url"] = thumbnail.group(1)

        # Method 2: oEmbed fallback
        try:
            oembed = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            oembed_response = requests.get(oembed)
            if oembed_response.status_code == 200:
                data = oembed_response.json()
                metadata["title"] = data.get("title", metadata["title"])
                metadata["author"] = data.get("author_name", metadata["author"])
                metadata["thumbnail_url"] = data.get("thumbnail_url", metadata["thumbnail_url"])
        except:
            pass

    except Exception as e:
        print(f"Error extracting YouTube metadata: {e}")

    return metadata

# Add YouTube transcript extraction

def get_youtube_transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([seg['text'] for seg in transcript])
    except Exception:
        return ""

# Update get_video_metadata to include transcript

def get_video_metadata(url):
    """Return video metadata for supported platforms."""
    if not url:
        raise ValueError("Please provide a video URL.")

    platform = get_video_platform(url)

    if platform == "youtube":
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL or missing video ID.")
        metadata = get_youtube_metadata(video_id)
        metadata["transcript"] = get_youtube_transcript(video_id)
        return metadata

    return {
        "title": f"Video on {platform}",
        "description": "",
        "thumbnail_url": f"https://via.placeholder.com/1280x720.png?text={platform}",
        "duration": 300,
        "views": 0,
        "author": f"{platform.capitalize()} Creator",
        "platform": platform,
        "video_id": "unknown",
        "transcript": ""
    }
