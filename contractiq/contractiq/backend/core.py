"""
ContractIQ — Core Module: Retrieval-Quality Evaluator
Grades retrieved passages as CORRECT / AMBIGUOUS / INCORRECT
and triggers corrective actions (re-retrieve, refine, discard).

Scope (50%): confidence-gated evaluator + corrective RAG loop.
Set DEMO_MODE=1 to run without downloading NLI / embedding models.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Literal, Tuple

Grade = Literal["CORRECT", "AMBIGUOUS", "INCORRECT"]
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"


@dataclass
class EvalResult:
    passage: str
    grade: Grade
    confidence: float
    reasoning: str


@dataclass
class CorrectionResult:
    original_query: str
    original_passages: List[str]
    grades: List[EvalResult]
    corrective_action: str  # "ACCEPT" | "RE_RETRIEVE" | "WEB_SEARCH"
    final_passages: List[str]
    final_answer: str
    was_corrected: bool
    mode: str = "live"


def _demo_available() -> bool:
    return DEMO_MODE or os.getenv("FORCE_DEMO", "0") == "1"


class RetrievalEvaluator:
    """Lightweight retrieval-quality evaluator using NLI + semantic similarity."""

    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-base"):
        self.demo = _demo_available()
        self.nli = None
        self.embedder = None

        if self.demo:
            return

        try:
            import torch
            from sentence_transformers import SentenceTransformer
            from transformers import pipeline

            self.nli = pipeline(
                "text-classification",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
            )
            self.embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        except Exception as exc:  # noqa: BLE001
            print(f"[ContractIQ] Model load failed ({exc}); using demo evaluator.")
            self.demo = True

    def grade_passage(self, query: str, passage: str, query_emb=None) -> EvalResult:
        if self.demo:
            return self._demo_grade(query, passage)

        from sentence_transformers import util

        nli_input = f"{passage} [SEP] This passage answers the question: {query}"
        nli_result = self.nli(nli_input, truncation=True, max_length=512)[0]

        if query_emb is None:
            query_emb = self.embedder.encode(query, convert_to_tensor=True)
        p_emb = self.embedder.encode(passage[:500], convert_to_tensor=True)
        sim = util.cos_sim(query_emb, p_emb).item()

        nli_score = (
            nli_result["score"]
            if nli_result["label"] == "ENTAILMENT"
            else (0.5 if nli_result["label"] == "NEUTRAL" else 0.1)
        )
        combined = 0.6 * nli_score + 0.4 * sim

        if combined > 0.7:
            grade: Grade = "CORRECT"
            reasoning = "Passage directly addresses the query with relevant content."
        elif combined > 0.4:
            grade = "AMBIGUOUS"
            reasoning = "Passage is partially relevant but may not fully answer the query."
        else:
            grade = "INCORRECT"
            reasoning = "Passage does not contain information relevant to the query."

        return EvalResult(
            passage=passage[:200] + "..." if len(passage) > 200 else passage,
            grade=grade,
            confidence=round(combined, 3),
            reasoning=reasoning,
        )

    def _demo_grade(self, query: str, passage: str) -> EvalResult:
        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        p_tokens = set(re.findall(r"[a-z0-9]+", passage.lower()))
        overlap = len(q_tokens & p_tokens) / max(len(q_tokens), 1)
        if overlap > 0.45:
            grade: Grade = "CORRECT"
            reasoning = "Demo grader: strong lexical overlap with the query."
            conf = min(0.92, 0.55 + overlap)
        elif overlap > 0.2:
            grade = "AMBIGUOUS"
            reasoning = "Demo grader: partial overlap; relevance uncertain."
            conf = 0.4 + overlap
        else:
            grade = "INCORRECT"
            reasoning = "Demo grader: little overlap with the query."
            conf = max(0.15, overlap)
        return EvalResult(
            passage=passage[:200] + "..." if len(passage) > 200 else passage,
            grade=grade,
            confidence=round(conf, 3),
            reasoning=reasoning,
        )

    def evaluate_retrieval(
        self, query: str, passages: List[str]
    ) -> Tuple[List[EvalResult], str]:
        # Efficiency: encode query once for all passage grades (live path)
        query_emb = None
        if not self.demo and self.embedder is not None:
            query_emb = self.embedder.encode(query, convert_to_tensor=True)

        grades = [
            self.grade_passage(query, p, query_emb=query_emb) for p in passages
        ]
        correct_count = sum(1 for g in grades if g.grade == "CORRECT")
        incorrect_count = sum(1 for g in grades if g.grade == "INCORRECT")

        if correct_count >= max(1, len(passages) * 0.5):
            action = "ACCEPT"
        elif incorrect_count >= max(1, len(passages) * 0.5):
            action = "WEB_SEARCH"
        else:
            action = "RE_RETRIEVE"
        return grades, action


class ContractQA:
    """End-to-end corrective RAG for contract documents."""

    def __init__(self):
        self.evaluator = RetrievalEvaluator()
        self.demo = self.evaluator.demo
        self.embedder = self.evaluator.embedder
        self.chunks: List[str] = []
        self.chunk_embeddings = None
        self._chunk_token_sets: List[set] = []
        try:
            import ollama  # noqa: F401

            self.use_ollama = not self.demo
        except ImportError:
            self.use_ollama = False

    @property
    def generator_model(self) -> str:
        if self.use_ollama and not self.demo:
            return "ollama:llama3.1:8b"
        return "extractive-lexical (no generative LLM)"

    def ingest_document(self, text: str, chunk_size: int = 500) -> int:
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        if not paragraphs:
            paragraphs = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size) if text[i : i + chunk_size].strip()]

        self.chunks = []
        for para in paragraphs:
            if len(para) > chunk_size:
                words = para.split()
                step = max(chunk_size // 5, 20)
                for i in range(0, len(words), step):
                    chunk = " ".join(words[i : i + step])
                    if len(chunk) > 50:
                        self.chunks.append(chunk)
            else:
                self.chunks.append(para)

        if not self.chunks and text.strip():
            self.chunks = [text.strip()[:chunk_size]]

        # Efficiency: pre-tokenize chunks once for lexical retrieval
        self._chunk_token_sets = [
            set(re.findall(r"[a-z0-9]+", c.lower())) for c in self.chunks
        ]

        if not self.demo and self.embedder is not None:
            self.chunk_embeddings = self.embedder.encode(
                self.chunks, convert_to_tensor=True
            )
        else:
            self.chunk_embeddings = None
        return len(self.chunks)

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        if not self.chunks:
            return []

        if self.demo or self.embedder is None or self.chunk_embeddings is None:
            q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            token_sets = self._chunk_token_sets or [
                set(re.findall(r"[a-z0-9]+", c.lower())) for c in self.chunks
            ]
            scored = [
                (len(q_tokens & c_tokens), chunk)
                for chunk, c_tokens in zip(self.chunks, token_sets)
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [c for _, c in scored[: min(top_k, len(scored))]]

        import torch
        from sentence_transformers import util

        q_emb = self.embedder.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(q_emb, self.chunk_embeddings)[0]
        top_indices = torch.topk(scores, min(top_k, len(self.chunks))).indices.tolist()
        return [self.chunks[i] for i in top_indices]

    def generate_answer(self, query: str, context: str) -> str:
        prompt = f"""Based ONLY on the following context, answer the question.
If the context doesn't contain the answer, say "Information not found in the document."

Context:
{context}

Question: {query}

Answer:"""

        if self.use_ollama and not self.demo:
            try:
                import ollama

                resp = ollama.chat(
                    model="llama3.1:8b",
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp["message"]["content"]
            except Exception:  # noqa: BLE001
                pass

        # Extractive / demo fallback
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if s.strip()]
        if not sentences:
            return "Information not found in the document."
        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        best = max(
            sentences,
            key=lambda s: len(q_tokens & set(re.findall(r"[a-z0-9]+", s.lower()))),
        )
        return best if best.endswith(".") else best + "."

    def query(self, question: str) -> CorrectionResult:
        passages = self.retrieve(question)
        if not passages:
            return CorrectionResult(
                original_query=question,
                original_passages=[],
                grades=[],
                corrective_action="WEB_SEARCH",
                final_passages=[],
                final_answer="Information not found in the document.",
                was_corrected=True,
                mode="demo" if self.demo else "live",
            )

        grades, action = self.evaluator.evaluate_retrieval(question, passages)
        was_corrected = action != "ACCEPT"

        if action == "ACCEPT":
            final_passages = [
                p for p, g in zip(passages, grades) if g.grade != "INCORRECT"
            ] or passages[:2]
        elif action == "RE_RETRIEVE":
            expanded = f"{question} details terms conditions obligations"
            final_passages = self.retrieve(expanded, top_k=7)
            new_grades, _ = self.evaluator.evaluate_retrieval(question, final_passages)
            final_passages = [
                p for p, g in zip(final_passages, new_grades) if g.grade != "INCORRECT"
            ] or final_passages[:3]
        else:
            # WEB_SEARCH stub — upcoming feature; keep best local passages
            final_passages = passages

        context = "\n\n".join(final_passages[:3])
        answer = self.generate_answer(question, context)

        return CorrectionResult(
            original_query=question,
            original_passages=passages,
            grades=grades,
            corrective_action=action,
            final_passages=final_passages,
            final_answer=answer,
            was_corrected=was_corrected,
            mode="demo" if self.demo else "live",
        )
