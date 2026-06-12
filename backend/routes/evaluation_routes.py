"""
FastAPI Routes — RAG Evaluation
================================
Supports automated quality checks, benchmark queries generation,
and evaluation reports exporting.
"""

import time
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from evaluation.ragas_evaluator import LocalRagasEvaluator
from utils.exporter import Exporter

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])

class BenchmarkRequest(BaseModel):
    questions_count: int = 3

class ExportRequest(BaseModel):
    run_id: str
    format: str = "txt"  # txt or pdf

@router.post("/generate-questions")
async def generate_benchmark_questions(request: BenchmarkRequest):
    """Automatically generate medical questions from document chunks."""
    from main import get_faiss_store, get_evaluator
    
    faiss_store = get_faiss_store()
    evaluator = get_evaluator()
    
    if faiss_store.vectorstore is None:
        raise HTTPException(
            status_code=400,
            detail="FAISS index is empty. Please upload documents and build index first."
        )

    all_docs = list(faiss_store.vectorstore.docstore._dict.values())
    if not all_docs:
        raise HTTPException(status_code=400, detail="No indexed chunks available to query.")

    try:
        dataset = evaluator.generate_benchmark_dataset(all_docs, count=request.questions_count)
        return {"questions": dataset}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate benchmark dataset: {exc}")

@router.post("/run")
async def run_benchmark_evaluation(questions: List[Dict[str, str]]):
    """Run automated RAGAS checks on a set of benchmark questions."""
    from main import get_retrieval_chain, get_evaluator
    
    chain = get_retrieval_chain()
    evaluator = get_evaluator()

    if not questions:
        raise HTTPException(status_code=400, detail="Questions dataset cannot be empty.")

    results = []
    
    for item in questions:
        question = item["question"]
        ground_truth = item.get("ground_truth", "")

        # Run query to retrieve contexts and response
        try:
            # Query standard pipeline
            res = chain.query(question, stream=False, strategy="hybrid")
            
            # Extract plain text context list
            contexts = [src.filename + f" (page {src.page_number}): " + question for src in res.sources]
            if not contexts:
                contexts = ["No matching context was retrieved."]
                
            # Grade
            metrics = evaluator.evaluate_turn(question, res.answer, contexts)
            
            results.append({
                "question": question,
                "answer": res.answer,
                "ground_truth": ground_truth,
                "metrics": metrics,
                "confidence": res.confidence
            })
        except Exception as exc:
            print(f"[ERROR] Failed to evaluate question '{question}': {exc}")
            continue

    if not results:
        raise HTTPException(status_code=500, detail="Failed to collect evaluation metrics for any question.")

    try:
        run_record = evaluator.save_run(results)
        return run_record
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save evaluation run: {exc}")

@router.get("/history")
async def get_evaluation_history():
    """Retrieve the log of all past quality checks."""
    from main import get_evaluator
    evaluator = get_evaluator()
    return evaluator.get_history()

@router.post("/export")
async def export_evaluation_report(request: ExportRequest):
    """Export an evaluation report as PDF or TXT."""
    from main import get_evaluator
    evaluator = get_evaluator()
    
    history = evaluator.get_history()
    target_run = None
    for run in history:
        if run["run_id"] == request.run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail="Requested evaluation run not found.")

    sections = []
    # Overall summary section
    summary_body = (
        f"Timestamp: {target_run['timestamp']}\n"
        f"Overall Quality Score: {target_run['overall_score']:.4f}\n\n"
        f"METRICS BREAKDOWN:\n"
        f"  - Faithfulness: {target_run['metrics']['faithfulness']:.4f}\n"
        f"  - Answer Relevancy: {target_run['metrics']['answer_relevancy']:.4f}\n"
        f"  - Context Precision: {target_run['metrics']['context_precision']:.4f}\n"
        f"  - Context Recall: {target_run['metrics']['context_recall']:.4f}\n"
    )
    sections.append({"header": "Overall Performance Metrics", "body": summary_body})

    # Add detail per query
    for idx, q in enumerate(target_run["queries"], 1):
        q_body = (
            f"Question: {q['question']}\n\n"
            f"Generated Answer:\n{q['answer']}\n\n"
            f"Ground Truth:\n{q['ground_truth']}\n\n"
            f"Scores:\n"
            f"  - Faithfulness: {q['metrics']['faithfulness']:.4f}\n"
            f"  - Answer Relevancy: {q['metrics']['answer_relevancy']:.4f}\n"
            f"  - Context Precision: {q['metrics']['context_precision']:.4f}\n"
            f"  - Context Recall: {q['metrics']['context_recall']:.4f}\n"
        )
        sections.append({"header": f"Query Test Case {idx}", "body": q_body})

    title = f"RAG Quality Evaluation Report - Run {request.run_id}"

    if request.format == "pdf":
        file_bytes = Exporter.to_pdf(title, sections)
        media_type = "application/pdf"
        filename = f"eval_report_{request.run_id}.pdf"
    else:
        file_bytes = Exporter.to_txt(title, sections)
        media_type = "text/plain"
        filename = f"eval_report_{request.run_id}.txt"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
