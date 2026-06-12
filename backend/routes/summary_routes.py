"""
FastAPI Routes — Research Summary Generator
============================================
Allows generating structured clinical summaries (Overview, Key Findings, etc.)
from uploaded medical literature.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
import json

from utils.exporter import Exporter

router = APIRouter(prefix="/summary", tags=["Summary"])

class SummaryRequest(BaseModel):
    topic: str

class SummaryResponse(BaseModel):
    topic: str
    overview: str
    key_findings: str
    risk_factors: str
    treatments: str
    research_gaps: str
    future_directions: str

class ExportSummaryRequest(BaseModel):
    topic: str
    overview: str
    key_findings: str
    risk_factors: str
    treatments: str
    research_gaps: str
    future_directions: str
    format: str = "txt"


@router.post("", response_model=SummaryResponse)
async def generate_research_summary(request: SummaryRequest):
    """Generate a structured clinical summary based on indexed medical documents."""
    from main import get_retriever, get_llm_client
    
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    retriever = get_retriever()
    llm_client = get_llm_client()

    # Search for relevant contexts (retrieve a higher count for broad summarization)
    scored_docs = retriever.retrieve(topic, k=8, strategy="hybrid", threshold=0.55)
    if not scored_docs:
        raise HTTPException(
            status_code=404, 
            detail="No relevant documents found in the database to summarize this topic."
        )

    context_text = "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('filename')}, Page {doc.metadata.get('page_number')}]\n{doc.page_content}"
        for doc, _ in scored_docs
    )

    system_prompt = (
        "You are an expert medical research assistant. Synthesize the provided context into a structured, "
        "evidence-based summary. Do not use outside knowledge. If information is missing, explicitly note it."
    )

    prompt = (
        f"Context:\n{context_text}\n\n"
        f"Generate a comprehensive research summary on the topic: '{topic}' using ONLY the context above.\n"
        f"Return the summary in the following strict JSON format (do not include markdown wrapper, return raw JSON):\n"
        "{\n"
        '  "overview": "<detailed overview section>",\n'
        '  "key_findings": "<bulleted key findings>",\n'
        '  "risk_factors": "<bulleted risk factors>",\n'
        '  "treatments": "<bulleted therapeutics or medication options>",\n'
        '  "research_gaps": "<bulleted missing areas or limitations in papers>",\n'
        '  "future_directions": "<bulleted directions for future clinical work>"\n'
        "}"
    )

    try:
        response = llm_client.generate(prompt, stream=False, system_prompt=system_prompt)
        # Parse JSON from response
        # Sometimes Qwen wraps in ```json ... ```, strip it
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        data = json_load_robust(cleaned)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate or parse summary report: {exc}")

    return SummaryResponse(
        topic=topic,
        overview=data.get("overview", "Information unavailable."),
        key_findings=data.get("key_findings", "Information unavailable."),
        risk_factors=data.get("risk_factors", "Information unavailable."),
        treatments=data.get("treatments", "Information unavailable."),
        research_gaps=data.get("research_gaps", "Information unavailable."),
        future_directions=data.get("future_directions", "Information unavailable.")
    )

def json_load_robust(text: str) -> dict:
    """Robust JSON parser that extracts JSON brackets if extra text is present."""
    try:
        return json.loads(text)
    except Exception:
        # Try finding the first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        raise ValueError("Response was not in valid JSON layout.")

@router.post("/export")
async def export_summary_report(request: ExportSummaryRequest):
    """Export a medical summary as plain text or PDF."""
    sections = [
        {"header": "Overview", "body": request.overview},
        {"header": "Key Findings", "body": request.key_findings},
        {"header": "Risk Factors", "body": request.risk_factors},
        {"header": "Treatments & Medications", "body": request.treatments},
        {"header": "Research Gaps", "body": request.research_gaps},
        {"header": "Future Research Directions", "body": request.future_directions}
    ]
    title = f"Medical Research Summary - {request.topic}"

    if request.format == "pdf":
        file_bytes = Exporter.to_pdf(title, sections)
        media_type = "application/pdf"
        filename = f"summary_{request.topic.replace(' ', '_')}.pdf"
    else:
        file_bytes = Exporter.to_txt(title, sections)
        media_type = "text/plain"
        filename = f"summary_{request.topic.replace(' ', '_')}.txt"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

