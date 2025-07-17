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
    description = video_metadata.get("description", "")
    transcript = video_metadata.get("transcript", "")
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

    # Add language-specific tag examples
    LANGUAGE_TAG_EXAMPLES = {
        "English": ["#music", "#video", "#tutorial"],
        "Spanish": ["#música", "#vídeo", "#tutorial"],
        "French": ["#musique", "#vidéo", "#tutoriel"],
        "German": ["#musik", "#video", "#tutorial"],
        "Italian": ["#musica", "#video", "#tutorial"],
        "Portuguese": ["#música", "#vídeo", "#tutorial"],
        "Hindi": ["#संगीत", "#वीडियो", "#ट्यूटोरियल"],
        "Japanese": ["#音楽", "#ビデオ", "#チュートリアル"],
        "Korean": ["#음악", "#비디오", "#튜토리얼"],
        "Chinese": ["#音乐", "#视频", "#教程"],
        "Russian": ["#музыка", "#видео", "#урок"],
        "Arabic": ["#موسيقى", "#فيديو", "#دروس"]
    }

    example_tags = LANGUAGE_TAG_EXAMPLES.get(language, LANGUAGE_TAG_EXAMPLES["English"])
    example_tags_str = ", ".join(example_tags)

    LANGUAGE_TITLE_EXAMPLES = {
        "English": "How to Make Music Videos Like a Pro",
        "Spanish": "Cómo hacer vídeos musicales como un profesional",
        "French": "Comment réaliser des clips musicaux comme un pro",
        "German": "Wie man Musikvideos wie ein Profi macht",
        "Italian": "Come realizzare video musicali come un professionista",
        "Portuguese": "Como fazer vídeos musicais como um profissional",
        "Japanese": "プロのようにミュージックビデオを作る方法",
        "Korean": "프로처럼 뮤직비디오 만드는 방법",
        "Chinese": "如何像专业人士一样制作音乐视频",
        "Russian": "Как снимать музыкальные клипы как профессионал",
        "Arabic": "كيفية عمل فيديوهات موسيقية مثل المحترفين"
    }
    example_title = LANGUAGE_TITLE_EXAMPLES.get(language, LANGUAGE_TITLE_EXAMPLES["English"])

    seo_template = f"""
    You are an SEO specialist and video content analyst.

    All output (tags, description, timestamps, titles) must be in {{language}}. Do NOT use English or any other language.

    For example, if the language is {language}, tags should look like: [{example_tags_str}]
    Example title in {language}: {example_title}
    Description, timestamps, and titles must also be in {language}.

    Video Title: {{title}}
    Platform: {{platform}}
    Video URL: {{video_url}}
    Description: {{description}}
    Transcript: {{transcript}}

    Tasks:
    1. Generate exactly {{num_timestamps}} timestamps with 'time' and 'description' fields, based on the actual content and structure of the video. 
       Use the transcript, description, and title to infer the main sections or topics. 
       Each timestamp should be unique and relevant to this specific video.
    2. All output (tags, description, timestamps, titles) must be in {language}. Do NOT use English or any other language. Titles must be in {language}. Example: {example_title}

    Respond ONLY with a valid JSON object with the following keys: 'tags', 'description', 'timestamps', and 'titles'.
    {{format_instructions}}

    Respond ONLY in {language}.
    """
    seo_prompt = PromptTemplate(
        input_variables=["platform", "title", "video_url", "description", "transcript", "num_timestamps", "language"],
        partial_variables={"format_instructions": seo_format_instructions},
        template=seo_template
    )

    seo_chain = LLMChain(llm=llm, prompt=seo_prompt)
    seo_result = seo_chain.run(
        platform=platform,
        title=title,
        video_url=video_url,
        description=description,
        transcript=transcript,
        num_timestamps=num_timestamps,
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

    # Step 3: Thumbnail Concepts Prompt (FIXED)
    thumbnail_parser = get_thumbnail_output_parser()
    thumbnail_format_instructions = thumbnail_parser.get_format_instructions()

    thumbnail_template = """
    You are a YouTube thumbnail designer. Based on the following video analysis and SEO recommendations:
    Title: {title}
    Platform: {platform}
    Analysis: {analysis}
    SEO: {seo}

    Generate 3 creative thumbnail concepts. For each, provide:
    - concept: Main idea
    - text_overlay: 3-5 word catchy text
    - colors: 3 hex codes
    - focal_point: Main visual focus
    - tone: Emotional tone
    - composition: Layout details

    {format_instructions}

    Respond in {language}.
    """
    thumbnail_prompt = PromptTemplate(
        input_variables=["platform", "title", "analysis", "seo", "language"],
        partial_variables={"format_instructions": thumbnail_format_instructions},
        template=thumbnail_template
    )
    thumbnail_chain = LLMChain(llm=llm, prompt=thumbnail_prompt)
    thumbnail_result = thumbnail_chain.run(
        platform=platform,
        title=title,
        analysis=analysis_result,
        seo=json.dumps(seo_data),
        language=language
    )
    try:
        thumbnail_data = parse_langchain_output(thumbnail_result)
    except Exception:
        thumbnail_data = generate_fallback_thumbnails(platform, language)

    return {
        "seo": seo_data,
        "analysis": analysis_result,
        "thumbnails": thumbnail_data
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
    TAGS_BY_LANGUAGE = {
        "English": ["youtube", "video", "tutorial", "vlog", "howto", "review", "explained", "educational", "learn", "step by step", "beginner", "advanced", "masterclass", "course", "lesson", "strategy", "technique", "demonstration", "walkthrough", "overview", "comparison", "versus", "top", "best", "recommended", "trending", "viral", "popular", "interesting", "amazing", "helpful", "useful", "informative", "detailed", "comprehensive"],
        "Spanish": ["youtube", "video", "tutorial", "vlog", "cómo", "reseña", "explicado", "educativo", "aprender", "paso a paso", "principiante", "avanzado", "maestría", "curso", "lección", "estrategia", "técnica", "demostración", "recorrido", "visión general", "comparación", "versus", "top", "mejor", "recomendado", "tendencia", "viral", "popular", "interesante", "asombroso", "útil", "informativo", "detallado", "integral"],
        "French": ["youtube", "vidéo", "tutoriel", "vlog", "comment", "critique", "expliqué", "éducatif", "apprendre", "étape par étape", "débutant", "avancé", "masterclass", "cours", "leçon", "stratégie", "technique", "démonstration", "visite guidée", "aperçu", "comparaison", "contre", "top", "meilleur", "recommandé", "tendance", "viral", "populaire", "intéressant", "incroyable", "utile", "informatif", "détaillé", "complet"],
        "German": ["youtube", "video", "tutorial", "vlog", "wie", "rezension", "erklärt", "lehrreich", "lernen", "schritt für schritt", "anfänger", "fortgeschritten", "meisterkurs", "kurs", "lektion", "strategie", "technik", "demonstration", "führung", "überblick", "vergleich", "gegen", "top", "beste", "empfohlen", "trend", "viral", "beliebt", "interessant", "erstaunlich", "hilfreich", "nützlich", "informativ", "detailliert", "umfassend"],
        "Italian": ["youtube", "video", "tutorial", "vlog", "come", "recensione", "spiegato", "educativo", "imparare", "passo dopo passo", "principiante", "avanzato", "masterclass", "corso", "lezione", "strategia", "tecnica", "dimostrazione", "guida", "panoramica", "confronto", "contro", "top", "migliore", "raccomandato", "tendenza", "virale", "popolare", "interessante", "incredibile", "utile", "informativo", "dettagliato", "completo"],
        "Portuguese": ["youtube", "vídeo", "tutorial", "vlog", "como", "revisão", "explicado", "educacional", "aprender", "passo a passo", "iniciante", "avançado", "masterclass", "curso", "lição", "estratégia", "técnica", "demonstração", "passeio", "visão geral", "comparação", "versus", "top", "melhor", "recomendado", "tendência", "viral", "popular", "interessante", "incrível", "útil", "informativo", "detalhado", "abrangente"],
        "Japanese": ["ユーチューブ", "ビデオ", "チュートリアル", "ブログ", "方法", "レビュー", "解説", "教育", "学ぶ", "ステップバイステップ", "初心者", "上級者", "マスタークラス", "コース", "レッスン", "戦略", "テクニック", "デモンストレーション", "ガイド", "概要", "比較", "対", "トップ", "ベスト", "おすすめ", "トレンド", "バイラル", "人気", "興味深い", "素晴らしい", "役立つ", "有益", "詳細", "包括的"],
        "Korean": ["유튜브", "비디오", "튜토리얼", "브이로그", "방법", "리뷰", "설명", "교육", "학습", "단계별", "초보자", "고급", "마스터클래스", "코스", "레슨", "전략", "기술", "시연", "가이드", "개요", "비교", "대", "최고", "베스트", "추천", "트렌드", "바이럴", "인기", "흥미로운", "놀라운", "유용한", "정보", "자세한", "포괄적"],
        "Chinese": ["油管", "视频", "教程", "博客", "方法", "评论", "讲解", "教育", "学习", "一步一步", "初学者", "高级", "大师班", "课程", "课程", "策略", "技术", "演示", "导览", "概述", "比较", "对比", "热门", "最佳", "推荐", "趋势", "病毒式", "流行", "有趣", "惊人", "有用", "信息", "详细", "全面"],
        "Russian": ["ютуб", "видео", "урок", "влог", "как", "обзор", "объяснение", "образование", "учиться", "шаг за шагом", "начинающий", "продвинутый", "мастер-класс", "курс", "урок", "стратегия", "техника", "демонстрация", "экскурсия", "обзор", "сравнение", "против", "топ", "лучший", "рекомендуемый", "тренд", "вирусный", "популярный", "интересный", "удивительный", "полезный", "информативный", "подробный", "всеобъемлющий"],
        "Arabic": ["يوتيوب", "فيديو", "برنامج تعليمي", "مدونة فيديو", "كيفية", "مراجعة", "مشروح", "تعليمي", "تعلم", "خطوة بخطوة", "مبتدئ", "متقدم", "دورة متقدمة", "دورة", "درس", "استراتيجية", "تقنية", "عرض", "جولة", "نظرة عامة", "مقارنة", "مقابل", "أفضل", "موصى به", "اتجاه", "فيروسي", "شائع", "مثير للاهتمام", "مذهل", "مفيد", "معلوماتي", "مفصل", "شامل"]
    }
    TITLES_BY_LANGUAGE = {
        "English": [
            {"rank": 1, "title": title, "reason": "Original title"},
            {"rank": 2, "title": f"Complete Guide to {title}", "reason": "Informative"},
            {"rank": 3, "title": f"How to {title}", "reason": "Step-by-step guide"},
            {"rank": 4, "title": f"Top 10 {title} Tips", "reason": "List format"},
            {"rank": 5, "title": f"{title} | Explained", "reason": "Educational"}
        ],
        "Spanish": [
            {"rank": 1, "title": title, "reason": "Título original"},
            {"rank": 2, "title": f"Guía completa de {title}", "reason": "Informativo"},
            {"rank": 3, "title": f"Cómo {title}", "reason": "Guía paso a paso"},
            {"rank": 4, "title": f"Top 10 consejos de {title}", "reason": "Formato de lista"},
            {"rank": 5, "title": f"{title} | Explicado", "reason": "Educativo"}
        ],
        "French": [
            {"rank": 1, "title": title, "reason": "Titre original"},
            {"rank": 2, "title": f"Guide complet de {title}", "reason": "Informatif"},
            {"rank": 3, "title": f"Comment {title}", "reason": "Guide étape par étape"},
            {"rank": 4, "title": f"Top 10 conseils pour {title}", "reason": "Format liste"},
            {"rank": 5, "title": f"{title} | Expliqué", "reason": "Éducatif"}
        ],
        "German": [
            {"rank": 1, "title": title, "reason": "Originaltitel"},
            {"rank": 2, "title": f"Komplette Anleitung zu {title}", "reason": "Informativ"},
            {"rank": 3, "title": f"Wie man {title}", "reason": "Schritt-für-Schritt-Anleitung"},
            {"rank": 4, "title": f"Top 10 Tipps zu {title}", "reason": "Listenformat"},
            {"rank": 5, "title": f"{title} | Erklärt", "reason": "Lehrreich"}
        ],
        "Italian": [
            {"rank": 1, "title": title, "reason": "Titolo originale"},
            {"rank": 2, "title": f"Guida completa a {title}", "reason": "Informativo"},
            {"rank": 3, "title": f"Come {title}", "reason": "Guida passo passo"},
            {"rank": 4, "title": f"Top 10 consigli su {title}", "reason": "Formato elenco"},
            {"rank": 5, "title": f"{title} | Spiegato", "reason": "Educativo"}
        ],
        "Portuguese": [
            {"rank": 1, "title": title, "reason": "Título original"},
            {"rank": 2, "title": f"Guia completo de {title}", "reason": "Informativo"},
            {"rank": 3, "title": f"Como {title}", "reason": "Guia passo a passo"},
            {"rank": 4, "title": f"Top 10 dicas de {title}", "reason": "Formato de lista"},
            {"rank": 5, "title": f"{title} | Explicado", "reason": "Educativo"}
        ],
        "Japanese": [
            {"rank": 1, "title": title, "reason": "オリジナルタイトル"},
            {"rank": 2, "title": f"{title}の完全ガイド", "reason": "情報提供"},
            {"rank": 3, "title": f"{title}の方法", "reason": "ステップバイステップガイド"},
            {"rank": 4, "title": f"{title}のトップ10のコツ", "reason": "リスト形式"},
            {"rank": 5, "title": f"{title} | 解説", "reason": "教育的"}
        ],
        "Korean": [
            {"rank": 1, "title": title, "reason": "원제목"},
            {"rank": 2, "title": f"{title} 완벽 가이드", "reason": "정보 제공"},
            {"rank": 3, "title": f"{title} 하는 방법", "reason": "단계별 가이드"},
            {"rank": 4, "title": f"{title}의 Top 10 팁", "reason": "리스트 형식"},
            {"rank": 5, "title": f"{title} | 설명", "reason": "교육적"}
        ],
        "Chinese": [
            {"rank": 1, "title": title, "reason": "原始标题"},
            {"rank": 2, "title": f"{title}完整指南", "reason": "信息丰富"},
            {"rank": 3, "title": f"如何{title}", "reason": "分步指南"},
            {"rank": 4, "title": f"{title}的十大技巧", "reason": "列表格式"},
            {"rank": 5, "title": f"{title} | 讲解", "reason": "教育性"}
        ],
        "Russian": [
            {"rank": 1, "title": title, "reason": "Оригинальное название"},
            {"rank": 2, "title": f"Полное руководство по {title}", "reason": "Информативно"},
            {"rank": 3, "title": f"Как {title}", "reason": "Пошаговое руководство"},
            {"rank": 4, "title": f"Топ 10 советов по {title}", "reason": "Формат списка"},
            {"rank": 5, "title": f"{title} | Объяснение", "reason": "Образовательно"}
        ],
        "Arabic": [
            {"rank": 1, "title": title, "reason": "العنوان الأصلي"},
            {"rank": 2, "title": f"الدليل الكامل لـ {title}", "reason": "معلوماتي"},
            {"rank": 3, "title": f"كيفية {title}", "reason": "دليل خطوة بخطوة"},
            {"rank": 4, "title": f"أفضل 10 نصائح لـ {title}", "reason": "تنسيق قائمة"},
            {"rank": 5, "title": f"{title} | شرح", "reason": "تعليمي"}
        ]
    }
    tags = TAGS_BY_LANGUAGE.get(language, TAGS_BY_LANGUAGE["English"])
    titles = TITLES_BY_LANGUAGE.get(language, TITLES_BY_LANGUAGE["English"])
    return {
        "tags": tags[:35],
        "description": f"This {platform} video about '{title}' provides valuable insights. Watch and enjoy!\n\n#YouTube #Tutorial",
        "timestamps": [{"time": "00:00", "description": "Introduction"}],
        "titles": titles
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
