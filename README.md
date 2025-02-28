# Documentation Scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A tool for keeping AI documentation up-to-date. Many AI models and APIs have rapidly changing documentation that can become outdated. This tool scrapes, processes, and summarizes documentation using GPT to help maintain current understanding of AI capabilities and features.

## Features

- Scrapes documentation from any website
- Processes text into optimized chunks
- Generates concise summaries using GPT
- Clean web interface and CLI options
- Automatic token management and optimization
- Download options for summaries and raw data

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env  # Then add your OpenAI API key

# Run web interface
python -m uvicorn app:app --reload

# Or use CLI
python main.py --url https://example.com
```

## Usage

### Web Interface
1. Open http://localhost:8000
2. Enter documentation URL
3. Set token limit (default: 32,000)
4. Add your OpenAI API key
5. Download generated summaries

### CLI
```bash
# Basic usage
python main.py --url https://example.com

# With options
python main.py --url https://example.com --token-limit 16000 --api-key YOUR_API_KEY

# Run specific modules
python main.py --module scraper --url https://example.com
python main.py --module processor
python main.py --module summarizer
python main.py --module combiner
```

## API Endpoints

- `POST /api/process`: Start processing a URL
- `POST /api/cancel`: Cancel current processing
- `GET /api/download/{type}`: Download results

## Requirements

- Python 3.10+
- OpenAI API key
- Required packages in `requirements.txt`

## Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Add OpenAI API key to `.env`
4. Run: `python -m uvicorn app:app --reload`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Create a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file 