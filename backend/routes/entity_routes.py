"""
FastAPI Routes — Medical Entity Extraction
==========================================
Extracts clinical entities (diseases, symptoms, treatments, medications, risk factors)
from medical texts using the local Qwen3 model.
"""

import json
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/entities", tags=["Entities"])

class EntityRequest(BaseModel):
    text: str

class EntityResponse(BaseModel):
    diseases: List[str] = []
    symptoms: List[str] = []
    treatments: List[str] = []
    medications: List[str] = []
    risk_factors: List[str] = []

@router.post("", response_model=EntityResponse)
async def extract_medical_entities(request: EntityRequest):
    """Extract clinical terms from the provided text snippet using Ollama Qwen3."""
    from main import get_llm_client
    
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text snippet cannot be empty.")

    llm_client = get_llm_client()

    system_prompt = (
        "You are an clinical NLP agent. Extract medical entities from text. "
        "Categorize them into: diseases, symptoms, treatments, medications, risk_factors."
    )

    prompt = (
        f"Input Text:\n{text}\n\n"
        f"Identify all clinical terms and return them in this exact JSON format (return ONLY raw JSON, no markdown wrapper):\n"
        "{\n"
        '  "diseases": ["list of diseases extracted"],\n'
        '  "symptoms": ["list of symptoms extracted"],\n'
        '  "treatments": ["list of therapeutics/treatments extracted"],\n'
        '  "medications": ["list of drugs/medications extracted"],\n'
        '  "risk_factors": ["list of risk factors extracted"]\n'
        "}"
    )

    try:
        response = llm_client.generate(prompt, stream=False, system_prompt=system_prompt)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        data = json_load_robust(cleaned)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Entity extraction parsed error: {exc}")

    return EntityResponse(
        diseases=data.get("diseases", []),
        symptoms=data.get("symptoms", []),
        treatments=data.get("treatments", []),
        medications=data.get("medications", []),
        risk_factors=data.get("risk_factors", [])
    )

def json_load_robust(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        raise ValueError("Response was not in valid JSON layout.")
