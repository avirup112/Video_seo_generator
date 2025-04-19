import groq
import json
import os
import streamlit as st

def analyze_video_with_groq(video_url, video_metadata, language="English"):
    """Analyze video content with platform-specific optimization using Groq"""
    if not os.environ.get("GROQ_API_KEY"):
        raise Exception("groq API key is required for analysis")

    client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))

    platform = video_metadata.get('platform', 'YouTube')

    analysis_prompt = f"""
    Analyze the {platform} video at {video_url} with title "{video_metadata.get('title', '')}".
    Provide a detailed analysis including:
    1. A summary of the video content (based on the title and any metadata)
    2. Main topics likely covered (at least 5 specific topics)
    3. Emotional tone and style of the video
    4. Target audience demographics and interests
    5. Content structure and flow

    Your analysis should be in {language} language.
    Make reasonable assumptions based on the available information.
    """

    analysis_response = client.chat.completions.create(
        model="Llama3-8b-8192",
        messages=[
            {"role": "system", "content": f"You are a video content analyst specialized in {platform} videos. Respond in {language}."},
            {"role": "user", "content": analysis_prompt}
        ],
        temperature=0.7,
    )

    analysis_result = analysis_response.choices[0].message.content

    duration = video_metadata.get('duration', 0)
    minutes = duration // 60
    num_timestamps = min(15, max(5, int(minutes / 2))) if minutes > 0 else 5

    seo_prompt = f"""
    Based on this analysis of a {platform} video titled "{video_metadata.get('title', '')}":
    {analysis_result}
    Generate comprehensive SEO recommendations optimized for {platform} including:
    1. Exactly 35 trending hashtags/tags
    2. SEO-optimized description (400-500 words)
    3. {num_timestamps} timestamps (duration: {duration} seconds)
    4. 5-7 alternative title suggestions

    Format as JSON:
    {{
        "tags": [...],  // 35 items
        "description": "...",
        "timestamps": [{{"time": "00:00", "description": "..."}}],
        "titles": [{{"rank": 1, "title": "...", "reason": "..."}}]
    }}
    """

    seo_response = client.chat.completions.create(
        model="Llama3-8b-8192",
        messages=[
            {"role": "system", "content": f"You are an SEO expert for {platform}."},
            {"role": "user", "content": seo_prompt}
        ],
        temperature=0.7
    )

    seo_result_text = seo_response.choices[0].message.content

    try:
        seo_result = json.loads(seo_result_text)
        if len(seo_result.get("tags", [])) != 35:
            seo_result["tags"] = ensure_exactly_35_tags(
                seo_result.get("tags", []), client, video_metadata, platform, language
            )
    except json.JSONDecodeError:
        try:
            json_start = seo_result_text.find('{')
            json_end = seo_result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                seo_result = json.loads(seo_result_text[json_start:json_end])
            else:
                seo_result = generate_fallback_seo(video_metadata, platform, language)
        except:
            seo_result = generate_fallback_seo(video_metadata, platform, language)

    thumbnail_prompt = f"""
    Based on this analysis of a {platform} video titled "{video_metadata.get('title', '')}":
    {analysis_result}
    Create 3 thumbnail concepts. For each:
    1. Main visual elements
    2. Text overlay (3-5 words)
    3. Color scheme (3 hex codes)
    4. Focal point
    5. Emotional tone
    6. Composition details

    Format:
    {{
        "thumbnail_concepts": [
            {{
                "concept": "...",
                "text_overlay": "...",
                "colors": ["#xxxxxx", "#xxxxxx", "#xxxxxx"],
                "focal_point": "...",
                "tone": "...",
                "composition": "..."
            }}
        ]
    }}
    """

    thumbnail_response = client.chat.completions.create(
        model="Llama3-8b-8192",
        messages=[
            {"role": "system", "content": f"You are a thumbnail designer for {platform}."},
            {"role": "user", "content": thumbnail_prompt}
        ]
    )

    thumbnail_result_text = thumbnail_response.choices[0].message.content

    try:
        thumbnail_result = json.loads(thumbnail_result_text)
    except json.JSONDecodeError:
        try:
            json_start = thumbnail_result_text.find('{')
            json_end = thumbnail_result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                thumbnail_result = json.loads(thumbnail_result_text[json_start:json_end])
            else:
                thumbnail_result = generate_fallback_thumbnails(platform, language)
        except:
            thumbnail_result = generate_fallback_thumbnails(platform, language)

    return {
        "analysis": analysis_result,
        "seo": seo_result,
        "thumbnails": thumbnail_result
    }

def ensure_exactly_35_tags(tags, client, video_metadata, platform, language):
    current_count = len(tags)
    if current_count == 35:
        return tags

    if current_count < 35:
        more_tags_prompt = f"""
        Based on existing tags for a {platform} video about "{video_metadata.get('title', '')}":
        {tags}
        Generate {35 - current_count} more trending tags in {language}. Only return JSON array.
        """
        try:
            more_tags_response = client.chat.completions.create(
                model="Llama3-8b-8192",
                messages=[{"role": "user", "content": more_tags_prompt}],
                temperature=0.7,
            )
            additional_tags = json.loads(more_tags_response.choices[0].message.content)
            tags.extend(additional_tags[:35 - current_count])
        except:
            for i in range(current_count, 35):
                tags.append(f"related_tag_{i}")
    elif current_count > 35:
        tags = tags[:35]

    return tags

def generate_fallback_seo(video_metadata, platform, language):
    title = video_metadata.get('title', 'Video Title')
    default_tags = ["youtube", "video", "tutorial", "vlog", "howto", "review", "explained",
                    "educational", "learn", "step by step", "beginner", "advanced", "masterclass",
                    "course", "lesson", "strategy", "technique", "demonstration", "walkthrough",
                    "overview", "comparison", "versus", "top", "best", "recommended", "trending",
                    "viral", "popular", "interesting", "amazing", "helpful", "useful", "informative",
                    "detailed", "comprehensive"]
    return {
        "tags": default_tags,
        "description": f"This {platform} video about '{title}' provides valuable insights. Watch and enjoy!\n\n#YouTube #Tutorial",
        "timestamps": [{"time": "00:00", "description": "Introduction"}],
        "titles": [
            {"rank": 1, "title": title, "reason": "Original title"},
            {"rank": 2, "title": f"Complete Guide to {title}", "reason": "Informative"},
            {"rank": 3, "title": f"How to {title}", "reason": "Step-by-step guide"},
            {"rank": 4, "title": f"Top 10 {title} Tips", "reason": "List format"},
            {"rank": 5, "title": f"{title} | Explained", "reason": "Educational"}
        ]
    }

def generate_fallback_thumbnails(platform, language):
    colors = ["#FF0000", "#FFFFFF", "#000000"]
    return {
        "thumbnail_concepts": [
            {
                "concept": "Professional layout with subject and bold text",
                "text_overlay": "Ultimate Guide",
                "colors": colors,
                "focal_point": "Centered subject",
                "tone": "Professional",
                "composition": "Text on left, subject on right"
            },
            {
                "concept": "Reaction-based thumbnail with close-up emotion",
                "text_overlay": "You Won't Believe!",
                "colors": colors,
                "focal_point": "Emotion-filled face",
                "tone": "Surprising",
                "composition": "Face close-up, text on top"
            },
            {
                "concept": "Before/After contrast",
                "text_overlay": "Transformation",
                "colors": colors,
                "focal_point": "Split screen",
                "tone": "Motivational",
                "composition": "Side-by-side comparison"
            }
        ]
    }
