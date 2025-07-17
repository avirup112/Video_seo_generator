# Video SEO Optimizer Pro

**Multilingual, Platform-Specific Video SEO Recommendations with AI**

---

## 🚀 Features

- Analyze YouTube and other video URLs for SEO optimization
- Supports multiple languages (English, Spanish, French, German, Italian, Portuguese, Japanese, Korean, Chinese, Russian, Arabic)
- Generates:
  - 35 trending tags
  - SEO-optimized description
  - Strategic timestamps
  - 5+ SEO-friendly titles
  - Platform-optimized thumbnails
- Modern Streamlit UI

---

## 🛠️ How It Works

```mermaid
flowchart TD
    A[User enters video URL & selects language/model]
    B[Fetch video metadata]
    C[Display video details & thumbnail]
    D[User clicks 'Generate SEO Recommendations']
    E{Model selection}
    F[Groq: Generate SEO fields]
    G[Langchain: Generate SEO fields]
    H[Display results: Content, Tags, Description, Timestamps, Titles, Thumbnails]
    I[User can copy tags, timestamps, download thumbnails, etc.]
    A --> B --> C --> D --> E
    E -- Groq --> F --> H
    E -- Langchain Agent --> G --> H
    H --> I
```

---

## 🖥️ Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys:**
   - Add your `GROQ_API_KEY` and (optionally) `STABILITY_API_KEY` in a `.env` file or via the Streamlit sidebar.

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

---




## 🤝 Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## 📧 Contact

For questions, bug reports, or feature requests, open an issue 
For direct inquires contact : avirupdasgupta3628@gmail.com

