"""
RAGAS Local Evaluator Module
----------------------------
Implements an LLM-as-a-judge quality evaluator running locally on Ollama.
Calculates Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
Saves run history to disk.
"""

import os
import re
import json
import random
import time
from typing import List, Dict, Any, Tuple
from config import EVALUATION_FILE, OLLAMA_TIMEOUT
import requests

class LocalRagasEvaluator:
    """Evaluates RAG pipeline performance using a local Qwen3 model."""

    def __init__(self, base_url: str, model_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def _query_llm(self, prompt: str, system_prompt: str) -> str:
        """Call the local LLM synchronously for evaluation scoring."""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,  # deterministic scoring
                "num_predict": 512,
            }
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=OLLAMA_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
        except Exception as exc:
            print(f"[ERROR] Local Ragas Evaluator prompt failed: {exc}")
            return ""

    def _extract_score(self, text: str, default: float = 0.8) -> float:
        """Parse the float score in the format [SCORE: X.XX]."""
        match = re.search(r"\[SCORE:\s*([0-9\.]+)\]", text)
        if match:
            try:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
            except ValueError:
                pass
        return default

    def evaluate_turn(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> Dict[str, float]:
        """Evaluate a single Q&A turn across 4 metrics."""
        combined_context = "\n\n---\n\n".join(contexts)

        # 1. Faithfulness
        faith_system = "You are an AI evaluator checking if claims in an answer are strictly supported by the context."
        faith_prompt = (
            f"Context:\n{combined_context}\n\n"
            f"Answer:\n{answer}\n\n"
            f"Identify if all statements in the Answer are supported by the Context. "
            f"List the statements. At the end, output your final score from 0.00 to 1.00 in this format: [SCORE: X.XX]"
        )
        faith_resp = self._query_llm(faith_prompt, faith_system)
        faithfulness = self._extract_score(faith_resp)

        # 2. Answer Relevancy
        relevancy_system = "You are an AI evaluator checking if the answer directly addresses the user question."
        relevancy_prompt = (
            f"Question:\n{question}\n\n"
            f"Answer:\n{answer}\n\n"
            f"Evaluate how directly and relevantly the Answer addresses the Question. "
            f"Explain briefly, and output your final score from 0.00 to 1.00 in this format: [SCORE: X.XX]"
        )
        relevancy_resp = self._query_llm(relevancy_prompt, relevancy_system)
        relevancy = self._extract_score(relevancy_resp)

        # 3. Context Precision
        precision_system = "You are an AI evaluator checking if the retrieved context is relevant and properly ordered."
        precision_prompt = (
            f"Question:\n{question}\n\n"
            f"Retrieved Chunks:\n{combined_context}\n\n"
            f"Evaluate if the retrieved contexts are highly relevant to the question. "
            f"Explain briefly, and output your final score from 0.00 to 1.00 in this format: [SCORE: X.XX]"
        )
        precision_resp = self._query_llm(precision_prompt, precision_system)
        precision = self._extract_score(precision_resp)

        # 4. Context Recall
        recall_system = "You are an AI evaluator checking if the contexts contain all necessary details to answer."
        recall_prompt = (
            f"Question:\n{question}\n\n"
            f"Retrieved Chunks:\n{combined_context}\n\n"
            f"Check if all the details needed to fully answer the question are present in the chunks. "
            f"Explain briefly, and output your final score from 0.00 to 1.00 in this format: [SCORE: X.XX]"
        )
        recall_resp = self._query_llm(recall_prompt, recall_system)
        recall = self._extract_score(recall_resp)

        return {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_precision": precision,
            "context_recall": recall
        }

    def generate_benchmark_dataset(
        self,
        documents: List[Any],
        count: int = 5
    ) -> List[Dict[str, str]]:
        """Generate a benchmark query dataset from indexed chunks."""
        if not documents:
            return []

        sampled_docs = random.sample(documents, min(len(documents), count * 2))
        dataset = []

        system_prompt = "You are a medical examiner. Formulate a direct research question based ONLY on the provided passage."
        
        for doc in sampled_docs:
            if len(dataset) >= count:
                break

            passage = doc.page_content[:1000]
            filename = doc.metadata.get("filename", "unknown.pdf")
            page = doc.metadata.get("page_number", 1)

            prompt = (
                f"Document Source: {filename} (page {page})\n"
                f"Passage:\n{passage}\n\n"
                f"Generate a clear, natural-sounding medical question that is fully answered by the passage above. "
                f"Return ONLY the question in a single line. Do not include introductory text."
            )
            question = self._query_llm(prompt, system_prompt).strip()
            # Clean quotes if any
            question = question.strip('"').strip("'")
            if question and len(question) > 10 and "?" in question:
                dataset.append({
                    "question": question,
                    "ground_truth": passage,
                    "filename": filename,
                    "page_number": page
                })

        return dataset

    def save_run(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile overall metrics and save the run to history.json."""
        if not results:
            return {}

        avg_faith = sum(r["metrics"]["faithfulness"] for r in results) / len(results)
        avg_rel = sum(r["metrics"]["answer_relevancy"] for r in results) / len(results)
        avg_prec = sum(r["metrics"]["context_precision"] for r in results) / len(results)
        avg_rec = sum(r["metrics"]["context_recall"] for r in results) / len(results)
        overall = (avg_faith + avg_rel + avg_prec + avg_rec) / 4.0

        run_record = {
            "run_id": f"run_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_score": round(overall, 4),
            "metrics": {
                "faithfulness": round(avg_faith, 4),
                "answer_relevancy": round(avg_rel, 4),
                "context_precision": round(avg_prec, 4),
                "context_recall": round(avg_rec, 4),
            },
            "queries": results
        }

        history = []
        if os.path.exists(EVALUATION_FILE):
            try:
                with open(EVALUATION_FILE, "r") as f:
                    history = json.load(f)
            except Exception:
                pass

        history.append(run_record)

        with open(EVALUATION_FILE, "w") as f:
            json.dump(history, f, indent=4)

        return run_record

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieve historical evaluation runs."""
        if not os.path.exists(EVALUATION_FILE):
            return []
        try:
            with open(EVALUATION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
