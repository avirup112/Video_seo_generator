from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.schema import HumanMessage, SystemMessage
import json
import re
import os


def get_seo_output_parser():
    response_schemas = [
        ResponseSchema(name="tags", description="A list of exactly 35 relevant hashtags/tags for the video"),
        ResponseSchema(name="description", description="A SEO-optimized video description between 400-500 words"),
        ResponseSchema(name="num_timestamps", description="A list of 5 timestamp objects with 'time' and 'description' fields"),
        ResponseSchema(name="titles", description="A list of title suggestion objects with 'rank','title' and 'reasons' fields"),
    ]
    return StructuredOutputParser.from_response_schemas(response_schemas)


def get_thumbnail_output_parser():
    response_schemas = [
        ResponseSchema(name="thumbnail_concepts", description="A list of 3 thumbnail concepts with all required fields")
    ]
    return StructuredOutputParser.from_response_schemas(response_schemas)


def run_seo_analysis_with_langchain(video_url, video_metadata, language="English"):
    if not os.environ.get("GROQ_API_KEY"):
        raise Exception("GROQ API key is required for analysis")

    llm = ChatGroq(temperature=0.7, model="llama3-8b-8192")  # <--- update this as needed

    platform = video_metadata.get("platform", "YouTube")
    title = video_metadata.get("title", "")
    duration = video_metadata.get("duration", 0)
    minutes = duration // 60
    num_timestamps = min(15, max(5, int(minutes / 2))) if minutes > 0 else 5

    # Step 1: Video Analysis Prompt
    analysis_template = """
    You are a video content analyst specialized in understanding {platform} videos, their structures, and audience appeal.
    Analyze the {platform} video at {video_url} titled "{title}".
    Provide a detailed analysis including:
    1. A summary of the video content (based on the title and metadata)
    2. Main topics likely covered (at least 5 specific topics)
    3. Emotional tone and style of the video
    4. Target audience demographics and interests
    5. Content structure and flow

    Respond in {language}.
    """
    analysis_prompt = PromptTemplate(
        input_variables=["platform", "video_url", "title", "language"],
        template=analysis_template
    )

    analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt)
    analysis_result = analysis_chain.run(
        platform=platform,
        video_url=video_url,
        title=title,
        language=language
    )

    # Step 2: SEO Recommendation Prompt
    seo_output_parser = get_seo_output_parser()
    seo_format_instructions = seo_output_parser.get_format_instructions()

    seo_template = """
    You are an SEO specialist focusing on optimizing {platform}
    content for maximum discovery and engagement.
    Based on this analysis of a {platform} video titled "{title}":
    {analysis}

    Generate comprehensive SEO recommendations optimized specifically for {platform} including:
    1. EXACTLY 35 trending hashtags/tags related to the video content.
    2. A 400-500 word SEO-optimized description including:
        - Engaging hook
        - Value proposition
        - Key topics with strategic keyword placement
        - CTA
        - Proper formatting
    3. Exactly {num_timestamps} timestamps with 'time' and 'description'.
    4. 5-7 SEO-optimized alternative title suggestions ranked with reasons.

    {format_instructions}

    Respond in {language}.
    """
    seo_prompt = PromptTemplate(
        input_variables=["platform", "title", "analysis", "num_timestamps", "duration", "language"],
        partial_variables={"format_instructions": seo_format_instructions},
        template=seo_template
    )

    seo_chain = LLMChain(llm=llm, prompt=seo_prompt)
    seo_result = seo_chain.run(
        platform=platform,
        title=title,
        analysis=analysis_result,
        num_timestamps=num_timestamps,
        duration=duration,
        language=language
    )

    try:
        seo_data = parse_langchain_output(seo_result)

        if len(seo_data.get("tags", [])) != 35:
            seo_data["tags"] = ensure_35_tags(
                seo_data.get("tags", []), llm, title, platform, language
            )
    except Exception:
        seo_data = generate_fallback_seo(title, platform, language)

    # Step 3: Thumbnail Instructions Format (if needed)
    thumbnail_parser = get_thumbnail_output_parser()
    thumbnail_format_instructions = thumbnail_parser.get_format_instructions()

    return {
        "seo": seo_data,
        "analysis": analysis_result,
        "thumbnail_format_instructions": thumbnail_format_instructions
    }


def parse_langchain_output(output_text):
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    match = re.search(json_pattern, output_text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    json_start = output_text.find('{')
    json_end = output_text.rfind('}')
    if json_start >= 0 and json_end > json_start:
        try:
            return json.loads(output_text[json_start:json_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse output as JSON")


def ensure_35_tags(tags, llm, title, platform, language):
    current_count = len(tags)
    if current_count == 35:
        return tags

    if current_count < 35:
        more_tags_template = """
        Based on these existing tags for a {platform} video about "{title}": {tags}
        Generate {num_needed} additional relevant and trending tags in {language}.
        Return ONLY a JSON array with the new tags.
        """
        more_tags_prompt = PromptTemplate(
            input_variables=["platform", "title", "tags", "num_needed", "language"],
            template=more_tags_template
        )
        more_tags_chain = LLMChain(llm=llm, prompt=more_tags_prompt)

        try:
            more_tags_result = more_tags_chain.run(
                platform=platform,
                title=title,
                tags=tags,
                num_needed=35 - current_count,
                language=language
            )
            additional_tags = parse_langchain_output(more_tags_result)
            if isinstance(additional_tags, list):
                tags.extend(additional_tags[:35 - current_count])
            else:
                for key in additional_tags:
                    if isinstance(additional_tags[key], list):
                        tags.extend(additional_tags[key][:35 - current_count])
                        break
        except:
            for i in range(current_count, 35):
                tags.append(f"related_tag_{i}")
    else:
        tags = tags[:35]

    return tags


def generate_fallback_seo(title, platform, language):
    youtube_tags = [
        "youtube", "video", "tutorial", "vlog", "howto", "review", "explained", "educational", "learn",
        "step-by-step", "beginner", "advanced", "masterclass", "course", "lesson", "strategy", "technique",
        "demonstration", "walkthrough", "overview", "comparison", "versus", "top", "best", "recommended",
        "trending", "viral", "popular", "interesting", "amazing", "helpful", "useful", "informative",
        "detailed", "comprehensive"
    ]
    return {
        "tags": youtube_tags[:35],
        "description": f"This YouTube video about {title} offers valuable insights and practical takeaways. "
                       f"Be sure to watch and gain a deeper understanding of the topic. \n\n"
                       f"Don't forget to like, comment, and subscribe for more!",
        "timestamps": [{"time": "00:00", "description": "Introduction"}],
        "titles": [
            {"rank": 1, "title": title, "reason": "Original title"},
            {"rank": 2, "title": f"Complete Guide to {title}", "reason": "Informative variant"},
            {"rank": 3, "title": f"How to {title} | Step by Step Tutorial", "reason": "Tutorial style"},
            {"rank": 4, "title": f"Top 10 {title} Tips You Need to Know", "reason": "List format"},
            {"rank": 5, "title": f"{title} | Explained Simply", "reason": "Education angle"},
        ]
    }


def generate_fallback_thumbnails(platform, language):
    youtube_colors = ["#FF0000", "#FFFFFF", "#000000"]
    return {
        "thumbnail_concepts": [
            {
                "concept": "Professional YouTube thumbnail with text overlay",
                "text_overlay": "Ultimate Guide",
                "colors": youtube_colors,
                "focal_point": "Center of the image with clear subject",
                "tone": "Professional and educational",
                "composition": "Subject on the right, text on the left with high contrast"
            },
            {
                "concept": "Emotional reaction thumbnail with facial expression",
                "text_overlay": "You Won't Believe This!",
                "colors": youtube_colors,
                "focal_point": "Close-up of surprised face or reaction",
                "tone": "Surprising and emotionally engaging",
                "composition": "Face takes up 40% of thumbnail with text above"
            },
            {
                "concept": "Before/After comparison thumbnail",
                "text_overlay": "Transformations",
                "colors": youtube_colors,
                "focal_point": "Split screen showing strong contrast",
                "tone": "Impressive and motivational",
                "composition": "50/50 split with arrow or divider in the middle"
            }
        ]
    }
