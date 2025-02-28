# Documentation Scraper

A clean, minimalistic web application for scraping, processing, and summarizing documentation using GPT-4o-mini.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch web interface (choose one):
python -m uvicorn app:app --reload        # Method 1 (recommended)
python -m uvicorn app:app                 # Method 2 (no auto-reload)
uvicorn app:app --reload                  # Method 3 (if uvicorn is in PATH)

# Or use command line
python main.py --url https://example.com --token-limit 32000 --api-key YOUR_API_KEY
```

Then open http://localhost:8000 in your browser.

## Web Interface

The web interface provides a clean, minimalistic experience with the following features:

### Input Options
- **URL Input**: Enter the documentation URL to scrape
- **Token Limit**: Set maximum combined token count (default: 32,000)
- **API Key**: Securely enter your OpenAI API key (never stored)

### Progress Tracking
- Real-time progress bar with percentage
- Detailed status messages with timestamps
- Color-coded success/failure indicators
- Cancellable processing at any stage

### Download Options
- Individual summaries (ZIP)
- Combined summary (single file)
- Optimized summaries (ZIP)
- Combined optimized summary (single file)
- Raw text chunks
- Original documentation

### Error Handling
- Clear error messages with timestamps
- Automatic retry on connection issues
- Invalid API key detection
- Token limit validation

## Features

- Clean, minimalistic black and white interface
- Scrapes documentation from any website
- Processes text into optimized chunks
- Generates summaries using GPT-4o-mini
- Automatic summary optimization if token limit is exceeded
- Intelligent summary combination into single documents
- Interactive command-line interface
- Independent module execution
- Download options for:
  - Individual summaries
  - Combined summary (all summaries in one file)
  - Optimized summaries
  - Combined optimized summary
  - Raw chunks
  - Original documentation
- Cancel processing at any stage
- Secure API key handling (never stored)

## Command Line Usage

### Interactive Mode

Running without arguments starts interactive mode:

```bash
python main.py
```

Interactive mode will:
- Present available modules to run
- Ask for required inputs
- Show default values where available
- Allow pressing Enter to use defaults

### Basic Usage

```bash
# Run all modules with default settings
python main.py --url https://example.com

# Specify maximum token limit for summaries
python main.py --url https://example.com --token-limit 16000

# Provide API key via command line
python main.py --url https://example.com --api-key YOUR_API_KEY
```

### Independent Module Execution

Run any module independently:

```bash
# Run web scraper only
python main.py --module scraper --url https://example.com

# Run text processor only (processes files in documentation/)
python main.py --module processor

# Run summarizer only (processes files in chunks/)
python main.py --module summarizer --token-limit 16000 --api-key YOUR_API_KEY

# Run combiner only (combines files in summaries/)
python main.py --module combiner
```

## Output Structure

The scraper generates several outputs:

### Directories
- `documentation/`: Scraped content files
- `chunks/`: Processed text chunks
- `summaries/`: Generated summaries
- `summaries/optimized/`: Optimized summaries (if token limit exceeded)

### Files
- `summaries/combined_summary.txt`: All summaries in one file
- `summaries/optimized/combined_summary.txt`: All optimized summaries in one file

## Token Management

- Default token limit: 32,000 tokens
- Valid range: 1,000 to 100,000 tokens
- Each chunk: max 16,000 tokens (GPT-4o-mini output limit)
- Input limit: 128,000 tokens (GPT-4o-mini input limit)

If summaries exceed the token limit:
1. Automatic optimization is triggered
2. Summaries are sorted by size
3. Batched processing is applied
4. More aggressive summarization
5. Original summaries are preserved

## API Usage

The application exposes these endpoints:

### `POST /api/process`
- Starts processing a URL
- Requires `X-API-Key` header
- Body: 
  ```json
  {
    "url": "https://example.com",
    "token_limit": 32000  // Optional, defaults to 32000
  }
  ```

### `POST /api/cancel`
- Cancels current processing
- Requires `X-API-Key` header

### `GET /api/download/{type}`
- Downloads results
- Types: 
  - `summaries`: Individual summaries (zip)
  - `combined`: All summaries in one file
  - `optimized`: Individual optimized summaries (zip)
  - `optimized_combined`: All optimized summaries in one file
  - `chunks`: Raw text chunks
  - `docs`: Original documentation
- Requires `X-API-Key` header

## Dependencies

Core requirements:
- Python 3.10+
- OpenAI API key (for GPT-4o-mini)
- Internet connection for web scraping

Python packages (install via `requirements.txt`):
- aiohttp: Async HTTP client/server
- beautifulsoup4: HTML parsing
- langdetect: Language detection
- openai: OpenAI API client
- httpx: HTTP client
- tiktoken: Token counting
- fastapi: Web framework
- uvicorn: ASGI server
- Additional utilities (see requirements.txt)

## Security

- API keys are never stored on the server
- All processing is done server-side
- CORS is enabled for all origins
- No sensitive data is exposed in the UI

## Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` file with:
   ```
   OPENAI_API_KEY=your_key_here
   ```
4. Run development server (choose one):
   ```bash
   # Method 1: Using python -m (recommended)
   python -m uvicorn app:app --reload

   # Method 2: Direct uvicorn (if in PATH)
   uvicorn app:app --reload
   ```

## Deployment

### Local Network

Run on your local network:
```bash
# Method 1: Using python -m (recommended)
python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Method 2: Direct uvicorn (if in PATH)
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Production

For production deployment:
```bash
# Method 1: Using python -m (recommended)
python -m uvicorn app:app --host 0.0.0.0 --port 80 --workers 4

# Method 2: Direct uvicorn (if in PATH)
uvicorn app:app --host 0.0.0.0 --port 80 --workers 4
```

### Common Options

- `--reload`: Enable auto-reload on code changes (development only)
- `--host 0.0.0.0`: Allow external access
- `--port 8000`: Set port number
- `--workers 4`: Number of worker processes (production)
- `--ssl-keyfile`: Path to SSL key file
- `--ssl-certfile`: Path to SSL certificate file

### GitHub Pages

1. Fork/clone repository
2. Enable GitHub Pages (Settings > Pages)
3. Set source to GitHub Actions
4. Push code to main branch
5. Access at https://username.github.io/repo

## License

MIT 

## Troubleshooting

### Common Issues

1. **"uvicorn not found" error**
   - Solution: Use `python -m uvicorn` instead of direct `uvicorn` command
   - Alternative: Add Python Scripts directory to PATH

2. **"API key is invalid" error**
   - Verify API key format
   - Check if API key has proper permissions
   - Ensure API key is for the correct OpenAI model

3. **"Token limit exceeded" warning**
   - Reduce token limit to below 100,000
   - Consider breaking documentation into smaller sections
   - Use optimized summaries for large documents

4. **"Failed to fetch URL" error**
   - Check if URL is accessible
   - Verify internet connection
   - Ensure URL points to valid documentation
   - Try using HTTPS instead of HTTP

5. **"Processing cancelled" message**
   - Normal if cancel button was clicked
   - Check for timeout issues if unexpected
   - Verify stable internet connection

### Performance Tips

1. **Optimal Token Limits**
   - Start with default 32,000 tokens
   - Increase if summaries are too brief
   - Decrease if processing is slow
   - Monitor optimization triggers

2. **Processing Speed**
   - Use local network deployment for faster access
   - Consider multiple worker processes in production
   - Avoid processing extremely large documentation sets at once
   - Use chunked processing for better performance

3. **Memory Usage**
   - Monitor system resources during processing
   - Clear browser cache if web interface becomes slow
   - Restart server if memory usage is high
   - Use production deployment for better resource management 