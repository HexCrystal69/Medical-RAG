"""
Analytics Tracker Module
-------------------------
Logs system metrics such as query count, processing latencies,
cited documents, and query classification. Computes summary stats.
"""

import os
import json
import time
from typing import List, Dict, Any
from config import ANALYTICS_FILE


class AnalyticsTracker:
    """Tracks and updates performance indicators and query metadata."""

    def __init__(self, filepath: str = ANALYTICS_FILE) -> None:
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                json.dump([], f)

    def _read_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_data(self, data: List[Dict[str, Any]]) -> None:
        try:
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as exc:
            print(f"[ERROR] Failed to save analytics data: {exc}")

    def log_query(
        self,
        query: str,
        retrieval_time: float,
        inference_time: float,
        referenced_docs: List[str],
        success: bool,
        strategy: str = "hybrid"
    ) -> None:
        """Append a query log entry with latency metrics and sources."""
        logs = self._read_data()
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "retrieval_time": round(retrieval_time, 4),
            "inference_time": round(inference_time, 4),
            "total_time": round(retrieval_time + inference_time, 4),
            "referenced_docs": referenced_docs,
            "success": success,
            "strategy": strategy
        }
        logs.append(entry)
        self._write_data(logs)

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Compile aggregated metrics from query logs."""
        logs = self._read_data()
        total_queries = len(logs)

        if total_queries == 0:
            return {
                "total_queries": 0,
                "avg_retrieval_time": 0.0,
                "avg_response_time": 0.0,
                "retrieval_success_rate": 100.0,
                "most_referenced_documents": [],
                "most_asked_topics": [],
                "strategy_distribution": {}
            }

        # Computations
        sum_retrieval = sum(log["retrieval_time"] for log in logs)
        sum_total = sum(log["total_time"] for log in logs)
        successes = sum(1 for log in logs if log["success"])

        # Strategy dist
        strategies: Dict[str, int] = {}
        for log in logs:
            strat = log.get("strategy", "hybrid")
            strategies[strat] = strategies.get(strat, 0) + 1

        # Referenced docs distribution
        doc_counts: Dict[str, int] = {}
        for log in logs:
            for doc in log["referenced_docs"]:
                doc_counts[doc] = doc_counts.get(doc, 0) + 1
        sorted_docs = [{"filename": k, "count": v} for k, v in doc_counts.items()]
        sorted_docs.sort(key=lambda x: x["count"], reverse=True)

        # Basic topic extraction from queries
        topics: Dict[str, int] = {}
        medical_terms = [
            "diabetes", "asthma", "copd", "stroke", "cancer", "renal", "kidney",
            "hypertension", "dementia", "alzheimer", "cardiac", "heart", "tuberculosis",
            "hepatitis", "pulmonary", "coronary"
        ]
        for log in logs:
            query_lower = log["query"].lower()
            found = False
            for term in medical_terms:
                if term in query_lower:
                    topics[term] = topics.get(term, 0) + 1
                    found = True
            if not found:
                # Count general words excluding short words
                words = [w for w in query_lower.split() if len(w) > 4]
                if words:
                    picked = words[0].strip("?.,!")
                    topics[picked] = topics.get(picked, 0) + 1

        sorted_topics = [{"topic": k, "count": v} for k, v in topics.items()]
        sorted_topics.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_queries": total_queries,
            "avg_retrieval_time": round(sum_retrieval / total_queries, 4),
            "avg_response_time": round(sum_total / total_queries, 4),
            "retrieval_success_rate": round((successes / total_queries) * 100.0, 2),
            "most_referenced_documents": sorted_docs[:5],
            "most_asked_topics": sorted_topics[:5],
            "strategy_distribution": strategies
        }
