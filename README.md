# agentic-ai-study-assistant
Here is your `README.md` completely overhauled to match that exact professional, emoji-rich, and highly structured format. 

You can copy and paste this directly into your repository!

***

# 📚 Agentic Study Assistant (AI + Multi-Agent Workflow)

An **Agentic AI-powered Study System** that automates learning workflows using **LangChain-based orchestration**, **multi-agent reasoning**, and **Retrieval-Augmented Generation (RAG)** over your personal study materials.

---

## 📌 1. The Learning Problem

Traditional studying methods are:
* Manual and time-consuming to summarize
* Passive reading without active recall
* Lack contextual help when you get stuck
* Require leaving your notes to search the web for explanations

👉 This leads to inefficiency, knowledge gaps, and a fragmented learning experience.

---

## 💡 2. Proposed Solution

To address these issues, we designed:
* 🤖 **AI-driven study engine (LangChain)**
* 🔄 **Retrieval-Augmented Generation (FAISS + RAG)**
* 🧠 Multi-Agent interactive quizzing and tutoring
* 🌐 Automated web research for knowledge gaps
* 📊 Structured JSON data for seamless UI rendering

---

## 🚀 3. Final Implemented System

We built a **hybrid Multi-Agent system** combining:

### 🧠 LangChain (Orchestration Engine)
* PDF text chunking and embedding
* Local FAISS vector storage
* LLM context routing

### 🤖 Multi-Agent System
* 🧠 **Summarizer Agent** → Condenses embedded notes into key bullet points
* 📝 **Quizzer Agent** → Generates strict JSON-formatted MCQs based only on the notes
* ⚠️ **Tutor Agent** → Provides contextual hints based on RAG data
* 🔎 **Research Agent** → Triggers Serper.dev web/YouTube searches when a student misses a quiz topic

### 🔄 Rate-Limit Automation
* Custom `_ThrottledGeminiEmbeddings` wrapper
* Prevents API exhaustion by auto-pacing embedding chunks

---

## 🔥 4. System Flow (End-to-End)

```text
User (Uploads PDF to Streamlit)
        ↓
LangChain + FAISS (Chunks & Embeds Data)
        ↓
Agent Reasoning Layer (Summarize / Quiz / Chat)
        ↓
Student Fails a Quiz Question?
        ↓
Trigger Research Agent (Serper API)
        ↓
Output Web Links & YouTube Tutorials 🔗
```

---

## 🛠️ 5. Tech Stack

### 🖥️ Frontend
* Streamlit (Custom UI & Chat Interface)

### ⚙️ Backend
* Python

### 🧠 AI / Agents
* LangChain & LangChain Core
* Google Gemini (`gemini-2.5-flash`)
* Google Embeddings (`gemini-embedding-001`)

### 🔄 External APIs
* Serper.dev (Google Search API)

### 📊 Data & Processing
* FAISS (Local Vector Database)
* PyPDFLoader
* Pydantic (Structured JSON Output)

---

## ⚙️ 6. How to Run Locally

### 1️⃣ Clone repository
```bash
git clone https://github.com/your-username/agentic-study-assistant.git
cd agentic-study-assistant
```

### 2️⃣ Create virtual environment
```bash
python -m venv venv
```

### 3️⃣ Activate environment
* **Windows:** `venv\Scripts\activate`
* **Mac/Linux:** `source venv/bin/activate`

### 4️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 5️⃣ Set Environment Variables
Create a file named `api.env` in the root folder:
```env
GOOGLE_API_KEY
SERPER_API_KEY=
```

### 6️⃣ Run application
```bash
streamlit run app.py
```

---

## 📊 7. Features

* ✅ AI-based note summarization (Grounded in RAG)
* ✅ Multi-agent study system
* ✅ Interactive MCQ generation
* ✅ Automated Web/YouTube research for weak topics
* ✅ Built-in Gemini API Rate-Limiting protection
* ✅ Session state memory for chat and quiz scores

---

## 📄 8. UI & Analytics Tracking

The system provides real-time session tracking:
* 📈 Live Quiz Score tracking
* 📊 "Topics Correct" vs "Topics to Review" lists
* 📌 Interactive chat history persistence

---

## ⚠️ 9. Challenges & Solutions

### 🔧 Free-Tier API Rate Limits (`429 RESOURCE_EXHAUSTED`)
* **Fixed:** Built a custom `_ThrottledGeminiEmbeddings` class to dynamically pause and batch chunking requests.

### 🧠 UI Crashing from Bad LLM Output
* **Fixed:** Forced the Quizzer Agent to use Pydantic `with_structured_output` to guarantee perfect JSON data for the Streamlit buttons.

### 📄 Model Versioning Errors (`404 NOT_FOUND`)
* **Fixed:** Updated API endpoints to explicitly call the latest supported Gemini models and embedding dimensions.

---

## 🎤 10. Viva Explanation (Short)

> This project is a Multi-Agent AI Study Assistant built with LangChain, Streamlit, and Google Gemini. It uses Retrieval-Augmented Generation (RAG) to turn static PDFs into interactive quizzes and summaries. If a student struggles with a concept, a dedicated Research Agent autonomously searches the web via the Serper API to provide targeted YouTube tutorials and articles.

---

## 🏆 Project Status

✔ Fully Functional  
✔ End-to-End RAG Pipeline  
✔ Multi-Agent Orchestration  
✔ Custom UI & Rate Limiting  

---

## 👤 Author

**Madamadakala Jashwanth Reddy**
Artificial Intelligence and Data Sceience Student

---

## ⭐ Support
If you like this project, give it a ⭐ on GitHub!
