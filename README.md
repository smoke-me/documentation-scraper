# Documentation Scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful tool for automated documentation analysis and summarization. This tool scrapes, processes, and summarizes documentation using GPT-4o-mini to help maintain current understanding of technical documentation, APIs, and features. It's particularly useful for keeping track of rapidly changing documentation in the AI and technology space.

## Features

- **Web Scraping**: Intelligent extraction of documentation from any website
- **Smart Text Processing**: Automatic chunking and optimization of content
- **AI-Powered Summarization**: Generates concise, accurate summaries using GPT-4o-mini
- **Token Optimization**: Automatic management of token limits with smart batching
- **Dual Interface**: Both web UI and CLI options available
- **Flexible Output**: Multiple output formats and optimization levels

## Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the web interface: `python -m uvicorn app:app --reload`
4. Open http://localhost:8000 in your browser

## Usage

### Web Interface
1. Navigate to http://localhost:8000
2. Enter the documentation URL you want to analyze
3. Set your desired token limit (default: 32,000)
4. Enter your OpenAI API key (only stored temporarily in memory)
5. Start the process and monitor progress
6. Download generated summaries

### CLI
```bash
# First set up your OpenAI API key in .env file:
# OPENAI_API_KEY=your_api_key_here

# Process a URL with default settings
python main.py --url https://example.com

# Customize processing
python main.py --url https://example.com --token-limit 16000 --api-key YOUR_API_KEY

# Run specific modules
python main.py --module scraper --url https://example.com
python main.py --module processor
python main.py --module summarizer
python main.py --module combiner
```

## Output Structure

The tool generates several output files and directories:

- `documentation/`: Raw scraped content
- `chunks/`: Processed text chunks
- `summaries/`: Individual section summaries
- `summaries/optimized/`: Token-optimized summaries (if needed)
- `combined_summary.txt`: Complete combined summary
- `optimized/combined_summary.txt`: Token-optimized combined summary

## API Endpoints

- `POST /api/process`: Start documentation processing
  - Parameters: `url`, `token_limit`, `api_key`
  - Returns: Server-sent events with progress updates
- `POST /api/cancel`: Cancel ongoing processing
- `GET /api/download/{type}`: Download results
  - Types: `summaries`, `chunks`, `docs`, `combined`, `optimized`

## Requirements

- Python 3.10 or higher
- OpenAI API key
- Dependencies listed in `requirements.txt`

## Development

1. Fork the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment:
   - Windows: `venv\Scripts\activate`
   - Unix/macOS: `source venv/bin/activate`
4. Install dev dependencies: `pip install -r requirements.txt`
5. Run tests: `python -m pytest`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests and ensure they pass
5. Create a Pull Request with a clear description

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 