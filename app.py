import os
import json
import asyncio
import zipfile
from io import BytesIO
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web_scraper import WebScraper
from text_processor import TextProcessor
from gpt_summarizer import GPTSummarizer
from summary_combiner import SummaryCombiner

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store active processes
active_processes: Dict[str, asyncio.Task] = {}

class ProcessRequest(BaseModel):
    url: str
    token_limit: int = 32000

async def process_documentation(request_id: str, url: str, api_key: str, token_limit: int):
    try:
        # Initial status
        yield json.dumps({
            "progress": 0,
            "status": "Starting process...",
            "complete": False
        }) + "\n"

        # Step 1: Web Scraping
        yield json.dumps({
            "progress": 5,
            "status": "Initializing web scraper...",
            "complete": False
        }) + "\n"

        scraper = WebScraper(url)
        await scraper.scrape_site()
        
        yield json.dumps({
            "progress": 25,
            "status": "Documentation scraped successfully",
            "complete": False
        }) + "\n"

        # Step 2: Text Processing
        yield json.dumps({
            "progress": 30,
            "status": "Processing text...",
            "complete": False
        }) + "\n"

        processor = TextProcessor()
        chunks = processor.process_files()
        
        yield json.dumps({
            "progress": 40,
            "status": "Creating text chunks...",
            "complete": False
        }) + "\n"

        processor.save_chunks(chunks)
        
        yield json.dumps({
            "progress": 50,
            "status": "Text processed and chunks created",
            "complete": False
        }) + "\n"

        # Step 3: Summary Generation
        yield json.dumps({
            "progress": 55,
            "status": "Initializing GPT summarizer...",
            "complete": False
        }) + "\n"

        summarizer = GPTSummarizer(api_key=api_key, target_token_limit=token_limit)
        await summarizer.process_chunks_async()
        
        yield json.dumps({
            "progress": 75,
            "status": "Summaries generated successfully",
            "complete": False
        }) + "\n"

        # Step 4: Combine Summaries
        yield json.dumps({
            "progress": 80,
            "status": "Combining summaries...",
            "complete": False
        }) + "\n"

        combiner = SummaryCombiner()
        combined = combiner.combine_summaries()
        
        yield json.dumps({
            "progress": 90,
            "status": "Summaries combined successfully",
            "complete": False
        }) + "\n"

        # Check available outputs
        yield json.dumps({
            "progress": 95,
            "status": "Checking available outputs...",
            "complete": False
        }) + "\n"

        has_optimized = os.path.exists(os.path.join('summaries', 'optimized'))
        has_combined = os.path.exists('combined_summary.txt')
        has_optimized_combined = os.path.exists(os.path.join('optimized', 'combined_summary.txt'))

        available = ["summaries", "chunks", "docs"]
        if has_optimized:
            available.append("optimized")
        if has_combined:
            available.append("combined")
        if has_optimized_combined:
            available.append("optimized_combined")

        yield json.dumps({
            "progress": 100,
            "status": "Process completed successfully",
            "complete": True,
            "available": available
        }) + "\n"

    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(f"Process error: {error_message}")  # Log error to console
        yield json.dumps({
            "progress": 0,
            "status": error_message,
            "complete": True,
            "available": []
        }) + "\n"
    finally:
        if request_id in active_processes:
            del active_processes[request_id]

@app.post("/api/process")
async def start_process(request: Request, process_request: ProcessRequest):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    # Validate token limit
    if process_request.token_limit < 1000 or process_request.token_limit > 100000:
        raise HTTPException(status_code=400, detail="Token limit must be between 1,000 and 100,000")

    request_id = str(hash(process_request.url + api_key))
    
    # Cancel existing process if any
    if request_id in active_processes:
        active_processes[request_id].cancel()
        del active_processes[request_id]

    async def event_stream():
        try:
            async for data in process_documentation(request_id, process_request.url, api_key, process_request.token_limit):
                yield data
        except asyncio.CancelledError:
            yield json.dumps({
                "progress": 0,
                "status": "Process cancelled by user",
                "complete": True,
                "available": []
            }) + "\n"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            print(f"Stream error: {error_message}")  # Log error to console
            yield json.dumps({
                "progress": 0,
                "status": error_message,
                "complete": True,
                "available": []
            }) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/cancel")
async def cancel_process(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    request_id = str(hash(request.query_params.get("url", "") + api_key))
    
    if request_id in active_processes:
        active_processes[request_id].cancel()
        del active_processes[request_id]
    
    return {"status": "cancelled"}

@app.get("/api/download/{type}")
async def download_results(type: str, request: Request):
    if type not in ["summaries", "chunks", "docs", "optimized", "combined", "optimized_combined"]:
        raise HTTPException(status_code=400, detail="Invalid download type")

    # Handle single file downloads
    if type in ["combined", "optimized_combined"]:
        filepath = os.path.join(
            "summaries",
            "optimized" if type == "optimized_combined" else "",
            "combined_summary.txt"
        )
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"No {type} summary available")
        return FileResponse(
            filepath,
            media_type="text/plain",
            filename=f"{type}_summary.txt"
        )

    # Handle directory downloads
    dir_map = {
        "summaries": "summaries",
        "chunks": "chunks",
        "docs": "documentation",
        "optimized": os.path.join("summaries", "optimized")
    }

    directory = dir_map[type]
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail=f"No {type} available")

    # Create zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(directory):
            for file in files:
                if file != "combined_summary.txt":  # Skip combined summary from zip
                    file_path = os.path.join(root, file)
                    arc_name = os.path.join(type, os.path.relpath(file_path, directory))
                    zip_file.write(file_path, arc_name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{type}.zip"'}
    )

@app.get("/")
async def root():
    return FileResponse("static/index.html") 