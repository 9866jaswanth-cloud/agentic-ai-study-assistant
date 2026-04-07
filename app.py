"""
Streamlit frontend for the Agentic Study Assistant.
"""

from __future__ import annotations

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

from engine import StudyEngine

load_dotenv(os.path.join(os.path.dirname(__file__), "api.env"))

# Avatars for st.chat_message (emoji work everywhere; avoids broken image URLs)
USER_AVATAR = "🧑‍💻"
AGENT_AVATAR = "🎓"


def _inject_app_styles() -> None:
    st.markdown(
        """
        <style>
            /* --- Warm yellow / cream palette --- */
            .stApp {
                background: linear-gradient(165deg, #fef08a 0%, #fde047 40%, #fef9c3 100%);
            }
            [data-testid="stHeader"] {
                background: rgba(254, 240, 138, 0.85);
                border-bottom: 1px solid rgba(202, 138, 4, 0.2);
            }
            .main .block-container {
                padding-top: 1.75rem;
                padding-bottom: 2.5rem;
                max-width: 920px;
            }
            .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
            .main label, .main p, .main span, .main li {
                color: #422006 !important;
            }
            /* Sidebar */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #fef08a 0%, #facc15 100%) !important;
                border-right: 1px solid rgba(202, 138, 4, 0.25) !important;
            }
            [data-testid="stSidebar"] .block-container {
                padding-top: 1.5rem;
            }
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span {
                color: #422006 !important;
            }
            [data-testid="stSidebar"] .stMarkdown { color: #713f12 !important; }
            /* Primary buttons */
            .stButton button[kind="primary"] {
                background: linear-gradient(135deg, #ca8a04 0%, #a16207 100%);
                color: #fffbeb !important;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                padding: 0.5rem 1rem;
            }
            .stButton button[kind="secondary"] {
                border-radius: 10px;
                border: 1px solid rgba(161, 98, 7, 0.35);
                background: rgba(255, 255, 255, 0.65);
                color: #713f12 !important;
            }
            /* Chat bubbles */
            [data-testid="stChatMessage"] {
                background: rgba(255, 255, 255, 0.88) !important;
                border: 1px solid rgba(202, 138, 4, 0.22) !important;
                border-radius: 16px !important;
                margin-bottom: 0.75rem !important;
                padding: 0.75rem 1rem !important;
                box-shadow: 0 2px 8px rgba(113, 63, 18, 0.08);
            }
            [data-testid="stChatMessage"] p {
                color: #422006 !important;
            }
            /* Expander */
            [data-testid="stExpander"] {
                background: rgba(255, 251, 235, 0.95);
                border: 1px solid rgba(202, 138, 4, 0.3);
                border-radius: 14px;
            }
            [data-testid="stExpander"] summary {
                color: #713f12 !important;
                font-weight: 600;
            }
            /* Chat input */
            [data-testid="stChatInput"] textarea {
                border-radius: 14px !important;
                border: 1px solid rgba(161, 98, 7, 0.3) !important;
                background: #fffbeb !important;
                color: #422006 !important;
            }
            /* Radio / success */
            .stRadio label { color: #422006 !important; }
            div[data-baseweb="radio"] { gap: 0.5rem; }
            .stSuccess, [data-testid="stAlert"] {
                border-radius: 12px;
            }
            /* Hero */
            .app-hero-title {
                font-size: 2.15rem;
                font-weight: 800;
                letter-spacing: -0.03em;
                background: linear-gradient(120deg, #a16207 0%, #854d0e 50%, #713f12 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.35rem;
            }
            .app-hero-sub {
                font-size: 1.02rem;
                color: #713f12;
                line-height: 1.6;
                max-width: 40rem;
                margin-bottom: 1.25rem;
            }
            .app-toolbar {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }
            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.35rem 0.65rem;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            .status-pill-ok {
                background: rgba(22, 163, 74, 0.2);
                color: #14532d;
                border: 1px solid rgba(22, 163, 74, 0.45);
            }
            .status-pill-wait {
                background: rgba(255, 255, 255, 0.55);
                color: #713f12;
                border: 1px solid rgba(161, 98, 7, 0.35);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session() -> None:
    defaults: dict = {
        "engine": None,
        "chat_messages": [],
        "quiz_questions": None,
        "quiz_index": 0,
        "quiz_correct_count": 0,
        "topics_correct": [],
        "topics_wrong": [],
        "latest_summary": None,
        "pending_quiz_celebration": False,
        "pdf_ready": False,
        "pdf_chunk_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _sync_pdf_status_from_engine() -> None:
    """Backfill sidebar status if a session has an embedded engine from before pdf_ready existed."""
    eng = st.session_state.get("engine")
    if eng is None or not getattr(eng, "ready", False):
        return
    chunks = getattr(eng, "_chunks", None)
    if chunks is not None and len(chunks) > 0:
        st.session_state.pdf_ready = True
        st.session_state.pdf_chunk_count = len(chunks)


def _append_chat(role: str, content: str) -> None:
    """Persist messages in session_state so they survive reruns."""
    st.session_state.chat_messages.append({"role": role, "content": content})


def _clear_chat_history() -> None:
    st.session_state.chat_messages = []


def _render_chat() -> None:
    for msg in st.session_state.chat_messages:
        role = msg["role"]
        if role not in ("user", "assistant"):
            role = "assistant"
        avatar = AGENT_AVATAR if role == "assistant" else USER_AVATAR
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### Notes & status")

        ready = bool(st.session_state.get("pdf_ready"))
        n = int(st.session_state.get("pdf_chunk_count") or 0)
        if ready:
            st.markdown(
                f'<span class="status-pill status-pill-ok">● Embedded · {n} chunks</span>',
                unsafe_allow_html=True,
            )
            st.caption("Vector index is ready for summarize & quiz.")
        else:
            st.markdown(
                '<span class="status-pill status-pill-wait">○ No PDF loaded</span>',
                unsafe_allow_html=True,
            )
            st.caption("Upload a PDF and tap **Process PDF** to embed.")

        st.divider()

        up = st.file_uploader("PDF file", type=["pdf"], label_visibility="collapsed")
        if up is not None:
            if st.button("Process PDF", type="primary", use_container_width=True):
                try:
                    eng = StudyEngine()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(up.getbuffer())
                        path = tmp.name
                    try:
                        with st.status("📄 Indexing your PDF…", expanded=True) as status:
                            st.write("Splitting pages and embedding text…")
                            n_chunks = eng.ingest_pdf(path)
                            status.update(
                                label=f"Indexed {n_chunks} chunks",
                                state="complete",
                                expanded=False,
                            )
                    finally:
                        os.unlink(path)
                    st.session_state.engine = eng
                    st.session_state.quiz_questions = None
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_correct_count = 0
                    st.session_state.latest_summary = None
                    st.session_state.pdf_ready = True
                    st.session_state.pdf_chunk_count = n_chunks
                    _append_chat(
                        "assistant",
                        f"Loaded your PDF into the vector store (**{n_chunks} chunks**). "
                        "Use **Summarize notes** or **Start quiz** when you're ready.",
                    )
                    st.success(f"Indexed {n_chunks} text chunks.")
                except Exception as e:  # noqa: BLE001
                    st.session_state.pdf_ready = False
                    st.session_state.pdf_chunk_count = 0
                    st.error(str(e))

        st.divider()
        st.markdown("**Session**")
        st.write(
            f"Topics correct: **{len(st.session_state.topics_correct)}** · "
            f"To review: **{len(st.session_state.topics_wrong)}**"
        )
        if st.session_state.topics_wrong:
            st.caption(
                "Review: " + ", ".join(sorted(set(st.session_state.topics_wrong)))
            )

        st.divider()
        if st.button("Clear chat history", use_container_width=True):
            _clear_chat_history()
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Study Assistant",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session()
    _sync_pdf_status_from_engine()
    _inject_app_styles()

    if st.session_state.pending_quiz_celebration:
        st.balloons()
        st.session_state.pending_quiz_celebration = False

    st.markdown('<p class="app-hero-title">Multi-Agent Study Assistant</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-hero-sub">Upload PDF notes — a <strong>Summarizer</strong> condenses ideas, '
        "a <strong>Quizzer</strong> tests you with grounded MCQs, and a "
        "<strong>Research</strong> agent finds extra resources when you miss a question. "
        "All responses use RAG over your file.</p>",
        unsafe_allow_html=True,
    )

    _render_sidebar()

    eng: StudyEngine | None = st.session_state.engine

    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        summarize = st.button(
            "Summarize notes",
            disabled=eng is None or not eng.ready,
            use_container_width=True,
        )
    with c2:
        start_quiz = st.button(
            "Start / reset quiz",
            disabled=eng is None or not eng.ready,
            use_container_width=True,
        )

    if summarize and eng:
        with st.status("🧠 Summarizer agent…", expanded=True) as status:
            st.write("Reading your vector store and condensing bullet points…")
            try:
                summary = eng.summarizer_agent()
            except Exception as e:  # noqa: BLE001
                summary = f"Error: {e}"
            status.update(label="Summary ready", state="complete", expanded=False)
        st.session_state.latest_summary = summary
        _append_chat(
            "assistant",
            "✅ **Summary ready** — expand **Your notes summary** below the toolbar.",
        )

    if start_quiz and eng:
        with st.status("📝 Quizzer agent…", expanded=True) as status:
            st.write("Retrieving context and generating 5 questions…")
            try:
                st.session_state.quiz_questions = eng.quizzer_agent()
                st.session_state.quiz_index = 0
                st.session_state.quiz_correct_count = 0
                status.update(label="Quiz ready", state="complete", expanded=False)
                _append_chat(
                    "assistant",
                    "Quiz ready — **5 questions** from your notes. Scroll to the quiz and submit each answer.",
                )
            except Exception as e:  # noqa: BLE001
                status.update(label="Quiz failed", state="error")
                _append_chat("assistant", f"Could not build quiz: {e}")

    if st.session_state.latest_summary:
        with st.expander("📋 Your notes summary", expanded=False):
            st.markdown(st.session_state.latest_summary)

    st.markdown("##### Chat")
    _render_chat()

    qs = st.session_state.quiz_questions
    if qs and eng:
        st.markdown("##### Quiz")
        idx = st.session_state.quiz_index
        if idx >= len(qs):
            st.success("You have finished all quiz questions.")
        else:
            q = qs[idx]
            labels = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(q["options"])]
            choice = st.radio(q["question"], labels, key=f"q_{idx}")
            submitted = st.button("Submit answer", key=f"sub_{idx}")

            if submitted:
                picked = labels.index(choice)
                correct = int(q["correct_index"])
                topic = (q.get("topic") or "this topic").strip()
                if picked == correct:
                    st.session_state.quiz_correct_count += 1
                    if topic not in st.session_state.topics_correct:
                        st.session_state.topics_correct.append(topic)
                    feedback = "Correct."
                    _append_chat("user", f"Q{idx + 1}: {choice}")
                    _append_chat("assistant", feedback)
                else:
                    if topic not in st.session_state.topics_wrong:
                        st.session_state.topics_wrong.append(topic)
                    correct_letter = chr(65 + correct)
                    feedback = (
                        f"Not quite — the best answer is **{correct_letter}**. "
                        f"Topic: _{topic}_."
                    )
                    with st.status("🔎 Research agent…", expanded=True) as status:
                        st.write("Finding a helpful link or video…")
                        try:
                            research = eng.research_agent(topic)
                        except Exception as e:  # noqa: BLE001
                            research = f"Research agent error: {e}"
                        status.update(label="Resources found", state="complete", expanded=False)
                    _append_chat("user", f"Q{idx + 1}: {choice}")
                    _append_chat("assistant", feedback + "\n\n" + research)

                st.session_state.quiz_index = idx + 1
                if st.session_state.quiz_index >= len(qs):
                    if st.session_state.quiz_correct_count == len(qs):
                        st.session_state.pending_quiz_celebration = True
                st.rerun()

    user_text = st.chat_input("Ask anything about your uploaded notes…")
    if user_text:
        _append_chat("user", user_text)
        if not eng or not eng.ready:
            reply = "Load a PDF in the sidebar and click **Process PDF** first. Then I can answer from your notes."
        else:
            with st.status("💬 Study Agent is answering from your notes…", expanded=True) as status:
                st.write("Searching your materials and drafting a reply…")
                try:
                    reply = eng.answer_question(user_text)
                    status.update(label="Reply ready", state="complete", expanded=False)
                except Exception as e:  # noqa: BLE001
                    status.update(label="Something went wrong", state="error")
                    reply = f"I couldn't complete that answer: {e}"
        _append_chat("assistant", reply)
        st.rerun()


if __name__ == "__main__":
    main()
