"""
RAG backend for the Agentic Study Assistant.
Uses LangChain, Gemini (chat) + FAISS + optional Serper for web research.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field


def _retry_after_seconds(message: str) -> Optional[float]:
    m = re.search(r"retry in ([0-9.]+)\s*s", message, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


class _ThrottledGeminiEmbeddings(Embeddings):
    """Spaces out embed calls to stay under free-tier limits; retries on 429."""

    def __init__(
        self,
        inner: GoogleGenerativeAIEmbeddings,
        *,
        texts_per_call: int = 12,
        min_interval_s: float = 0.58,
        max_retries: int = 12,
    ) -> None:
        self._inner = inner
        self._texts_per_call = max(1, texts_per_call)
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: List[List[float]] = []
        last_end = 0.0
        for start in range(0, len(texts), self._texts_per_call):
            if start > 0:
                elapsed = time.monotonic() - last_end
                nap = self._min_interval_s - elapsed
                if nap > 0:
                    time.sleep(nap)
            batch = texts[start : start + self._texts_per_call]
            attempt = 0
            while True:
                try:
                    out.extend(self._inner.embed_documents(batch))
                    last_end = time.monotonic()
                    break
                except Exception as e:  # noqa: BLE001
                    err = str(e)
                    if (
                        "429" in err or "RESOURCE_EXHAUSTED" in err
                    ) and attempt < self._max_retries:
                        attempt += 1
                        wait = _retry_after_seconds(err) or min(
                            40.0 + attempt * 12.0,
                            120.0,
                        )
                        time.sleep(wait)
                        continue
                    raise
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(text)


class QuizItem(BaseModel):
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)
    topic: str = Field(
        ...,
        description="Short topic label for follow-up research if the student is wrong",
    )


class QuizBatch(BaseModel):
    questions: List[QuizItem] = Field(..., min_length=5, max_length=5)


class StudyEngine:
    """Builds a FAISS index from a PDF and exposes summarizer, quizzer, and research agents."""

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
    ) -> None:
        self._google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        if not self._google_api_key:
            raise ValueError("GOOGLE_API_KEY is required (env or constructor).")

        self._serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")

        chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
        self._llm = ChatGoogleGenerativeAI(
            model=chat_model,
            google_api_key=self._google_api_key,
            temperature=0.2,
        )
        base_emb = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=self._google_api_key,
        )
        if os.getenv("GEMINI_EMBED_NO_THROTTLE", "").lower() in ("1", "true", "yes"):
            self._embeddings = base_emb
        else:
            self._embeddings = _ThrottledGeminiEmbeddings(
                base_emb,
                texts_per_call=int(os.getenv("GEMINI_EMBED_TEXTS_PER_CALL", "12")),
                min_interval_s=float(os.getenv("GEMINI_EMBED_MIN_INTERVAL_S", "0.58")),
                max_retries=int(os.getenv("GEMINI_EMBED_MAX_RETRIES", "12")),
            )

        self._vectorstore: Optional[FAISS] = None
        self._chunks: List[Document] = []

    @property
    def ready(self) -> bool:
        return self._vectorstore is not None and bool(self._chunks)

    def ingest_pdf(self, pdf_path: str) -> int:
        """Load PDF, split, embed into local FAISS. Returns number of chunks stored."""
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2800,
            chunk_overlap=200,
        )
        self._chunks = splitter.split_documents(docs)
        self._vectorstore = FAISS.from_documents(self._chunks, self._embeddings)
        return len(self._chunks)

    def _context_from_store(self, query: str, k: int = 12) -> str:
        if not self._vectorstore:
            raise RuntimeError("No documents loaded. Upload and process a PDF first.")
        docs = self._vectorstore.similarity_search(query, k=k)
        parts = [d.page_content for d in docs]
        return "\n\n---\n\n".join(parts)

    def _full_notes_context(self, max_chars: int = 100_000) -> str:
        """Join stored chunks for summarization (within a safe character budget)."""
        if not self._chunks:
            raise RuntimeError("No documents loaded. Upload and process a PDF first.")
        buf: List[str] = []
        total = 0
        for d in self._chunks:
            t = d.page_content
            if total + len(t) > max_chars:
                buf.append(t[: max(0, max_chars - total)])
                break
            buf.append(t)
            total += len(t)
        return "\n\n".join(buf)

    def summarizer_agent(self) -> str:
        """Condense vector-store material into concise bullet points."""
        notes = self._full_notes_context()
        prompt = (
            "You are a study assistant. Read the notes below (from the user's PDF) and "
            "produce a clear summary as bullet points only. "
            "Do not invent facts; stay grounded in the text.\n\n"
            f"NOTES:\n{notes}"
        )
        resp = self._llm.invoke(prompt)
        return getattr(resp, "content", str(resp))

    def answer_question(self, question: str, *, retrieval_k: int = 14) -> str:
        """Answer a student question using only retrieved passages from the PDF (RAG)."""
        q = (question or "").strip()
        if not q:
            return "Please type a question about your notes."
        context = self._context_from_store(q, k=retrieval_k)
        prompt = (
            "You are a friendly study tutor. The student uploaded course notes (excerpts below).\n"
            "Answer their question clearly and helpfully for learning.\n"
            "Rules:\n"
            "- Use ONLY the CONTEXT below. If the answer is not there, say you cannot find it "
            "in their notes and suggest they rephrase or check a different section—do not guess.\n"
            "- Use short paragraphs or bullet points when it helps.\n"
            "- If you quote ideas, keep them faithful to the context.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"STUDENT QUESTION:\n{q}"
        )
        resp = self._llm.invoke(prompt)
        return getattr(resp, "content", str(resp))

    def quizzer_agent(self) -> List[dict[str, Any]]:
        """Generate exactly 5 multiple-choice questions as structured data, RAG-only."""
        context = self._context_from_store(
            "main concepts definitions procedures examples key terms",
            k=16,
        )
        structured = self._llm.with_structured_output(QuizBatch)
        prompt = (
            "You write exam-style multiple-choice questions for students.\n"
            "Rules:\n"
            "- Use ONLY the CONTEXT below. Do not use outside knowledge.\n"
            "- Exactly 5 questions.\n"
            "- Each question has exactly 4 options (A–D).\n"
            "- One clearly correct answer per question.\n"
            "- For each question, set `topic` to a short phrase (2–6 words) describing "
            "the concept being tested, for later web search if the student misses it.\n\n"
            f"CONTEXT:\n{context}"
        )
        batch: QuizBatch = structured.invoke(prompt)
        return [q.model_dump() for q in batch.questions]

    def research_agent(self, topic: str) -> str:
        """Search the web for a helpful article or YouTube resource on `topic`."""
        if not self._serper_api_key:
            return (
                "Web search is disabled. Add SERPER_API_KEY to your environment "
                "(e.g. api.env) to enable study links from the Research agent."
            )
        serper = GoogleSerperAPIWrapper(serper_api_key=self._serper_api_key)
        query = f'{topic} explained tutorial (site:youtube.com OR site:edu OR guide)'
        try:
            payload = serper.results(query)
        except Exception as e:  # noqa: BLE001
            return f"Search failed: {e}"

        lines: List[str] = []
        organic = payload.get("organic") or []
        for hit in organic[:5]:
            title = hit.get("title") or ""
            link = hit.get("link") or ""
            if link:
                lines.append(f"- **{title}** — {link}")

        if not lines and isinstance(payload.get("answerBox"), dict):
            ab = payload["answerBox"]
            link = ab.get("link") or ""
            if link:
                lines.append(f"- {link}")

        if not lines:
            return serper.run(query)

        return "Here are resources that may help:\n\n" + "\n".join(lines)
