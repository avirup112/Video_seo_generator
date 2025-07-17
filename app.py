import os 
import streamlit as st 
from groq import Groq
from dotenv import load_dotenv
import json
import time
import tempfile
from PIL import Image
from io import BytesIO
import requests
import re

from utils.video_extractor import get_video_metadata
from utils.seo_agents import run_seo_analysis_with_langchain
from utils.thumbnails import generate_thumbnail,create_thumbnail_preview

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

LANGUAGES = [
    "English","Spanish","French","German","Italian",
    "Portuguese",
    "Japanese","Korean","Chinese","Russian","Arabic"
]

st.set_page_config(
    page_title = "Video SEO optimizer",
    layout = "wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
     .main-title { font-size: 2.5rem; color: #1E88E5; margin-bottom: 1rem; }
     .section-title { font-size: 1.5rem; color: #0D47A!; margin-top: 1rem; }
     .tag-pill { background-color: #E3F2FD; color: #1565C0; padding: 5px 10px; border-radius: 15px; margin: 2px; display:inline-block; }
     .timestamp-card { background-color: #2196F3; color: #FFFFFF; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
     .stButton>button { background-color:#1E88E5; color:white; }
     .platform-badge { font-weight: bold; padding: 5px 10px; border-radius: 5px; display: inline-block; margin-bottom: 10px; }
     .youtube-badge { background-color : #FF0000; color:white; }
     .thumbnail-concept { border: 1px solid #DDDDDD; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
     .color-switch {height :25px; width:25px; display:inline-block; margin-right: 5px; border: 1px solid #CCCCCC; }
<style>
""",unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/assistant.png", width=125)
    st.title("API configuration")
    
    groq_api_key = st.text_input("GROQ API Key",type="password",key="groq key")
    stability_api_key = st.text_input("Stability AI API Key",type="password",key="stability key")
    
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key
    if stability_api_key:
        os.environ["STABILITY_API_KEY"] = stability_api_key
        
    st.divider()
    
    st.subheader("Language Settings")
    selected_language = st.selectbox("Select Output Language",LANGUAGES,index=0)
    
    st.subheader("Model Settings")
    model_option = st.selectbox(
        "Select AI Engine",
        ["Groq","Langchain Agent"],
        index=1,
        help="Choose between direct Groq API calls or Langhcian agent system"
    )
    
    st.divider()
    st.subheader("About")
    st.write("""
    This tool uses AI to analyzed videos and generate platform-specific SEO recommendations.
    
    It optimizes:
    -35 Trending Tags
    -Detailed Descriptions
    -Strategic Timestamps
    -5+ SEO-friendly Titles
    -Platform-optimized THumbnails
    """)
    
    st.divider()
    st.caption("Created with Groq,Langchain & Streamlit")
    
#Main content
st.markdown("<h1 class='main-title'>Video SEO Optimizer Pro</h1>",unsafe_allow_html=True)
st.write("Analyze video form YouTube to generate Platform-specific SEO recommendations.")


video_url = st.text_input("Enter video URL",placeholder="https://www.youtube.com/watch?v=...")

if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'video_metadata' not in st.session_state:
    st.session_state.video_metadata = None
if 'video_url' not in st.session_state:
    st.session_state.video_url = ""
    
if video_url:
    st.session_state.video_url = video_url
    try:
        with st.spinner("Fetching video Information...."):
            metdata = get_video_metadata(video_url)
            st.session_state.video_metadata = metdata
        
        col1,col2=st.columns([2,1])
        
        with col1:
            st.subheader('Video Details')
            
            platform = metdata.get('platform','Unknown') if metdata else 'Unknown'
            badge_class = f"{platform.lower()}-badge" if platform in ["YouTube","Instagram","LinkedIn"] else ""
            st.markdown(f"<div class='platform-badge {badge_class}'>{platform}</div>",unsafe_allow_html=True)
            
            st.write(f"**Title:** {metdata.get('author','N/A') if metdata else 'N/A'}")
            
            if metdata and metdata.get('duration'):
                minutes = metdata.get('duration') // 60
                seocnds = metdata.get('duration') % 60
                st.write(f"**Duration:** {minutes} minutes {seocnds} seconds")
                
            if metdata and metdata.get('views'):
                st.write(f"**Views:** {metdata.get('views',0):,}")
        
        with col2:
            if metdata and metdata.get('thumbnail_url'):
                st.image(metdata['thumbnail_url'], caption="Current Thumbnail", use_container_width=True)
                
        st.write(f"Analysis will be perfomed in **{selected_language}** using **{model_option}**")
        if st.button(f"Generate SEO Recommendations"):
            if not os.environ.get("GROQ_API_KEY"):
                st.error("Please enter your Groq API Key in the sidebar.")
            else:
                with st.spinner(f"Analyzing video content and generating  optimized SEO recommendations in{selected_language}..."):
                    try:
                        if model_option =="Langchain Agent":
                            results = run_seo_analysis_with_langchain(
                                video_url,
                                st.session_state.video_metadata,language=selected_language
                            )
                        else:
                            from analysis_function import analyze_video_with_groq
                            results = analyze_video_with_groq(video_url, st.session_state.video_metadata, language=selected_language)
                        
                        st.session_state.analysis_results = results
                        st.session_state.analysis_complete = True
                    
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
    except Exception as e:
        st.error(f"Erorr processing video URL: {str(e)}")
        
if st.session_state.analysis_complete and st.session_state.analysis_results:
    results = st.session_state.analysis_results
    
    st.success("Analysis Complete! Here are your SEO recommendations:")
    
    tabs = st.tabs(["Content Analysis","Tags (35)","Description","Timestamps","Titles (5+)","Thumbnails"])
    
    with tabs[0]:
        st.markdown("<h2 class='section-title'>Content Analysis</h2",unsafe_allow_html=True)
        st.write(results["analysis"])
     
    with tabs[1]:
        st.markdown("<h2 class='section-title'>35 Recommended Tags</h2",unsafe_allow_html=True)
        st.write("Use these trending tags to improve your video's discoverability:")   
        
        tag_columns = st.columns(3)
        tags = results["seo"]["tags"]
        # Remove related_tag_xx
        tags = [tag for tag in tags if not tag.startswith("related_tag")]
        tags_per_column = len(tags) // 3 + (1 if len(tags) % 3 > 0 else 0)
        
        for i, col in enumerate(tag_columns):
            with col:
                for j in range(i * tags_per_column, min((i + 1) * tags_per_column, len(tags))):
                    if j < len(tags):
                        st.markdown(f"<div classs='tag-pill'>#{tags[j]}</div>",unsafe_allow_html=True)
                        
        st.info(f"Total tags: {len(tags)} - Optimized for {st.session_state.video_metadata.get('platform','YouTube') if st.session_state.video_metadata else 'YouTube'}")
        
        if st.button("Copy All Tags"):
            tags_text = " ".join([f"#{tag}" for tag in tags])
            st.code(tags_text)
            st.success("Tags copied! Use ctrl+C to copt to clipboard.")
    
    with tabs[2]:
        st.markdown("<h2 class='section-title'>Platform-Optimized Description</h2>",unsafe_allow_html=True)
        platform = st.session_state.video_metadata.get('platform','Youtube') if st.session_state.video_metadata else 'Youtube'
        st.write(f"Use this SEO-optimized description for your:{platform}video:") 
        
        description = results["seo"]["description"]
        st.text_area("Copy this description",description,height=300)
        
        word_count = len(description.split())
        char_count = len(description)
        col1,col2 = st.columns(2)
        with col1:
            st.info(f"Word count:{word_count} words")
        with col2:
            st.info(f"Character count:{char_count} characters")
            
    with tabs[3]:
        st.markdown("<h2 class='section-title'>Video Timestamps</h2>",unsafe_allow_html=True)
        st.write("Add these timestamps to your description to improve user navigation:")
        
        timestamps = results["seo"].get("timestamps", [])
        timestamp_text =""
        
        for ts in timestamps:
            st.markdown(f"<div class='timestamp-card'><b>{ts['time']}</b>-{ts['description']}</div>",unsafe_allow_html=True)
            timestamp_text += f"{ts['time']} - {ts['description']}\n"
        
        duration = st.session_state.video_metadata.get('duration',0) if st.session_state.video_metadata else 0
        st.info(f"Total Timestamps:{len(timestamps)} - Optimized for a {duration // 60} minute video") 
        
        if st.button("Copy All Timestamps"):
            st.code(timestamp_text)
            st.success("Timestamps copied! Use ctrl+C to copy to clipboard.")
            
        st.markdown("""
        **How to use timestamps in YouTube:**
        1.Copy these timestamps to your video description
        2.Make sure each timestamp is on a new line
        3.The format must be exactly as shown(00:00 - Description)
        4.Timestamps will automatically become clickable links in YouTube
        
        **Benefits of using timestamps:**
        -Inrecased user experienece and navigation
        -Increased watch time and engagement
        -Better visibility in Youtube Search
        -More professional appearence
        """)
        
    with tabs[4]:
        st.markdown("<h2 class='section-title'>Title suggestions</h2>",unsafe_allow_html=True)
        st.write("Try these title options to imrpove click-throughrate:")
        titles = results["seo"]["titles"]
        # Do not filter titles by language; show all generated titles
        for title in titles:
            col1,col2=st.columns([1,5])
            with col1:
                st.markdown(f"<h3>#{title['rank']}</h3>",unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h3>{title['title']}</h2>",unsafe_allow_html=True)
                if "reason" in title:
                    st.markdown(f"<i>{title['reason']}</i>",unsafe_allow_html=True)
                char_count = len(title['title'])
                platform = st.session_state.video_metadata.get('platform','YouTube') if st.session_state.video_metadata else 'YouTube'
                char_limit = 60 if platform == "YouTube" else 100
                status = "Good length" if char_count <= char_limit else "Too long"
                st.write(f"{char_count}/{char_limit} characters - {status}")
    
    with tabs[5]:
        st.markdown("<h2 class='section-title'>AI-Generated Thumbnail Concepts<h2>",unsafe_allow_html=True)
        platform = st.session_state.video_metadata.get('platform','YouTube') if st.session_state.video_metadata else 'YouTube'
        st.write(f"Here are thumbnail concepts specifically designed for {platform}:")
        thumbnail_concepts = results["thumbnails"]["thumbnail_concepts"]
        for i, concept in enumerate(thumbnail_concepts):
            st.markdown(f"<div class='thumbnail-concept'>",unsafe_allow_html=True)
            st.markdown(f"### Concept {i+1}:{concept.get('text_overlay','Concept')}")
            col1, col2 = st.columns([3,2])
            with col1:
                st.markdown(f"**Concept:** {concept.get('concept','N/A')}")
                st.markdown(f"**Text Overlay:** {concept.get('text_overlay','N/A')}")
                st.markdown("**Colors:**")
                if 'colors' in concept and isinstance(concept['colors'], list):
                    color_html = ""
                    for color in concept['colors']:
                        color_html += (
                            f"<span style='display:inline-block;width:24px;height:24px;background:{color};"
                            f"border-radius:4px;margin-right:4px;border:1px solid #ccc;vertical-align:middle;'></span>"
                            f"<span style='margin-right:12px;vertical-align:middle;'>{color}</span>"
                            )
                    st.markdown(color_html, unsafe_allow_html=True)
                st.markdown(f"**Focal Point:** {concept.get('focal_point','N/A')}")
                st.markdown(f"**Emotional Tone:** {concept.get('tone','N/A')}")
                if "composition" in concept:
                    st.markdown(f"**Composition:** {concept['composition']}")
            with col2:
                from utils.thumbnails import generate_thumbnail_with_stability, create_thumbnail_preview
                import os
                if os.environ.get("STABILITY_API_KEY"):
                    preview = generate_thumbnail_with_stability(concept, st.session_state.video_metadata.get('title', ''))
                    if preview:
                        st.image(preview, caption="AI-generated thumbnail preview")
                    else:
                        st.warning("Could not generate thumbnail with Stability AI.")
                else:
                    preview = create_thumbnail_preview(concept, st.session_state.video_metadata.get('title', ''))
                    st.image(preview, caption="Thumbnail preview")
            st.markdown("</div",unsafe_allow_html=True)
        platform = st.session_state.video_metadata.get('platform','YouTube') if st.session_state.video_metadata else 'YouTube'
        st.info(f"{platform} thumbnails are optimized for the platform recommended dimensions")
        st.markdown("""
        **About AI-generated thumbnails:**The thumbnails are generated using Stability AI based on your video's content analysis.
        Each thumbnail includes the suggested text overlay directly on the image. These are ready-to-use thumbnails that you can download and upload directly to your video platform.
        """)

st.divider()
st.caption("Video SEO Optimizer Pro . Multilingual Optimization . Platform-Specific recommended")