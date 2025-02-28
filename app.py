import os
import json
import asyncio
import zipfile
import signal
import atexit
import sys
from io import BytesIO
from typing import Dict, List, Set
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web_scraper import WebScraper
from text_processor import TextProcessor
from gpt_summarizer import GPTSummarizer
from summary_combiner import SummaryCombiner
from clean import cleanup_files
from starlette.background import BackgroundTask

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

# Store active processes and their states
active_processes: Dict[str, asyncio.Task] = {}
active_connections: Set[str] = set()
shutdown_event = asyncio.Event()

def cleanup_for_request(request_id: str):
    """Clean up resources for a specific request."""
    if request_id in active_processes:
        try:
            active_processes[request_id].cancel()
        except Exception:
            pass
        del active_processes[request_id]
    
    if request_id in active_connections:
        active_connections.remove(request_id)
    
    # Only clean files if this was the last active connection
    if not active_connections:
        cleanup_files()

async def shutdown():
    """Cleanup when the server shuts down."""
    print("\nCleaning up before exit...")
    # Cancel all active processes
    for process in active_processes.values():
        try:
            process.cancel()
        except Exception:
            pass
    active_processes.clear()
    active_connections.clear()
    
    # Clean up all generated files
    cleanup_files()
    shutdown_event.set()

# Register cleanup for normal shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await shutdown()

# Register cleanup for system signals
def signal_handler(signum, frame):
    """Handle system signals for cleanup."""
    # Create a new event loop for cleanup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination request

# Register cleanup on normal exit
atexit.register(cleanup_files)

# Middleware to handle client disconnection and page reloads
@app.middleware("http")
async def check_client_disconnect(request: Request, call_next):
    # Generate request ID
    request_id = str(hash(request.query_params.get("url", "") + request.headers.get("X-API-Key", "")))
    
    try:
        # Add to active connections
        active_connections.add(request_id)
        
        # Handle the request
        response = await call_next(request)
        
        # Add cleanup task for streaming responses
        if isinstance(response, StreamingResponse):
            cleanup_task = BackgroundTask(cleanup_for_request, request_id)
            response.background = cleanup_task
        
        return response
        
    except Exception as e:
        # Handle disconnection or error
        cleanup_for_request(request_id)
        if "Client disconnected" in str(e) or "Disconnected" in str(e):
            print(f"Client disconnected: {request_id}")
        raise
    finally:
        # Ensure connection is removed if there's an error
        if request_id in active_connections:
            active_connections.remove(request_id)
            if not active_connections:  # If this was the last connection
                cleanup_files()

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

        combiner = SummaryCombiner(max_tokens=token_limit)
        combined = combiner.combine_summaries()
        
        # Get token counts from combined summaries
        import tiktoken
        tokenizer = tiktoken.get_encoding("cl100k_base")
        
        total_tokens = 0
        if os.path.exists('combined_summary.txt'):
            with open('combined_summary.txt', 'r', encoding='utf-8') as f:
                content = f.read()
                total_tokens = len(tokenizer.encode(content))
        
        # Report token count and optimization status
        if total_tokens > token_limit:
            yield json.dumps({
                "progress": 85,
                "status": f"Initial summary exceeds token limit ({total_tokens}/{token_limit} tokens). Starting optimization...",
                "complete": False
            }) + "\n"
            
            # Wait for optimized summary
            optimized_path = 'optimized_combined_summary.txt'
            for _ in range(30):  # Wait up to 30 seconds
                if os.path.exists(optimized_path):
                    with open(optimized_path, 'r', encoding='utf-8') as f:
                        optimized_content = f.read()
                        optimized_tokens = len(tokenizer.encode(optimized_content))
                    yield json.dumps({
                        "progress": 90,
                        "status": f"Optimization complete. Final token count: {optimized_tokens}/{token_limit}",
                        "complete": False
                    }) + "\n"
                    break
                await asyncio.sleep(1)
        else:
            yield json.dumps({
                "progress": 85,
                "status": f"Summary within token limit ({total_tokens}/{token_limit} tokens). No optimization needed.",
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
        has_optimized_combined = os.path.exists('optimized_combined_summary.txt')

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
        cleanup_for_request(request_id)

    async def event_stream():
        try:
            async for data in process_documentation(request_id, process_request.url, api_key, process_request.token_limit):
                yield data
        except asyncio.CancelledError:
            cleanup_for_request(request_id)
            yield json.dumps({
                "progress": 0,
                "status": "Process cancelled by user",
                "complete": True,
                "available": []
            }) + "\n"
        except Exception as e:
            cleanup_for_request(request_id)
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
        },
        background=BackgroundTask(cleanup_for_request, request_id)
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
        filepath = (
            "optimized_combined_summary.txt"
            if type == "optimized_combined"
            else "combined_summary.txt"
        )
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"No {type} summary available")
        
        # Read file content and return as StreamingResponse
        async def file_stream():
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            file_stream(),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{type}_summary.txt"',
                "Cache-Control": "no-cache",
                "Content-Type": "text/plain; charset=utf-8"
            }
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
    
    # Stream the zip file
    async def zip_stream():
        while chunk := zip_buffer.read(8192):
            yield chunk
        zip_buffer.close()
    
    return StreamingResponse(
        zip_stream(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{type}.zip"',
            "Cache-Control": "no-cache"
        }
    )

@app.get("/")
async def root():
    return FileResponse("static/index.html") 