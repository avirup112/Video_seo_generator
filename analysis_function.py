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
