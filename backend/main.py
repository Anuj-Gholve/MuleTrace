"""
main.py
FastAPI application — upload CSV and run detection pipeline.
"""

from __future__ import annotations

import io
import logging
import traceback

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from detection_engine import run_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MuleTrace",
    version="1.0.0",
)

# CORS — allow Vite dev server and common origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Accept a CSV file, run the detection pipeline, return results JSON."""
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    # Read and parse CSV
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        df = pd.read_csv(io.BytesIO(contents))
        logger.info(f"CSV loaded: {len(df)} rows, columns: {list(df.columns)}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"CSV parse error: {exc}")
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {exc}")

    # Run detection pipeline
    try:
        result = run_pipeline(df)
        logger.info(
            f"Pipeline complete: {result['summary']['total_accounts_analyzed']} accounts, "
            f"{result['summary']['suspicious_accounts_flagged']} suspicious, "
            f"{result['summary']['fraud_rings_detected']} rings"
        )
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error(f"Pipeline error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Detection pipeline error: {exc}")

    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
