import os
import sys
import asyncio
import argparse
from web_scraper import WebScraper
from text_processor import TextProcessor
from gpt_summarizer import GPTSummarizer
from summary_combiner import SummaryCombiner

def is_web_server():
    """Check if running as a web server."""
    return 'UVICORN' in os.environ or any('uvicorn' in arg.lower() for arg in sys.argv)

def get_interactive_input(prompt: str, default: str = None) -> str:
    """Get input from user with default value support."""
    if default:
        prompt = f"{prompt} (default: {default}, press Enter for default): "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default

async def run_scraper(url: str) -> bool:
    """Run the web scraper module independently."""
    try:
        print("Running Web Scraper...")
        scraper = WebScraper(url)
        await scraper.scrape_site()
        print(f"✓ Content scraped to documentation/")
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def run_processor() -> bool:
    """Run the text processor module independently."""
    try:
        print("Running Text Processor...")
        processor = TextProcessor()
        chunks = processor.process_files()
        if chunks:
            processor.save_chunks(chunks)
            print(f"✓ Chunks saved to chunks/")
            return True
        print("✗ No valid chunks were generated")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

async def run_summarizer(token_limit: int, api_key: str = None) -> bool:
    """Run the GPT summarizer module independently."""
    try:
        print("Running GPT Summarizer...")
        if not api_key:
            api_key = get_interactive_input("Enter your OpenAI API key")
            if not api_key:
                print("✗ API key is required")
                return False
        
        summarizer = GPTSummarizer(target_token_limit=token_limit, api_key=api_key)
        await summarizer.process_chunks_async()
        print(f"✓ Summaries generated")
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def run_combiner() -> bool:
    """Run the summary combiner module independently."""
    try:
        print("Running Summary Combiner...")
        combiner = SummaryCombiner()
        combined = combiner.combine_summaries()
        
        if 'combined' in combined:
            print("✓ Combined summary saved to summaries/combined_summary.txt")
        if 'optimized_combined' in combined:
            print("✓ Combined optimized summary saved to summaries/optimized/combined_summary.txt")
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

async def main():
    parser = argparse.ArgumentParser(description='Documentation Scraper CLI')
    parser.add_argument('--url', help='URL to scrape documentation from')
    parser.add_argument('--token-limit', type=int, help='Maximum combined token count for summaries (default: 32000)')
    parser.add_argument('--api-key', help='OpenAI API key')
    parser.add_argument('--module', choices=['scraper', 'processor', 'summarizer', 'combiner'],
                      help='Run a specific module independently')
    args = parser.parse_args()

    # Interactive mode if no arguments provided and not running as web server
    if not any(vars(args).values()) and not is_web_server():
        print("Welcome to Documentation Scraper Interactive Mode!")
        print("Press Enter to use default values where available.\n")
        
        if not args.module:
            modules = ['all', 'scraper', 'processor', 'summarizer', 'combiner']
            print("Available modules:")
            for i, module in enumerate(modules, 1):
                print(f"{i}. {module}")
            module_choice = get_interactive_input("Select module number", "1")
            args.module = modules[int(module_choice) - 1] if module_choice.isdigit() and 1 <= int(module_choice) <= len(modules) else 'all'
        
        if args.module in ['all', 'scraper']:
            args.url = get_interactive_input("Enter documentation URL")
        
        if args.module in ['all', 'summarizer']:
            args.token_limit = int(get_interactive_input("Enter token limit", "32000"))
            args.api_key = get_interactive_input("Enter OpenAI API key")
    
    # Set defaults
    token_limit = args.token_limit or 32000
    success = True

    try:
        # Run specific module or all
        if args.module == 'scraper':
            if not args.url:
                print("URL is required for scraper module")
                sys.exit(1)
            success = await run_scraper(args.url)
        
        elif args.module == 'processor':
            success = run_processor()
        
        elif args.module == 'summarizer':
            success = await run_summarizer(token_limit, args.api_key)
        
        elif args.module == 'combiner':
            success = run_combiner()
        
        else:  # Run all modules
            if not args.url:
                print("URL is required for full process")
                sys.exit(1)
            
            # Step 1: Web Scraping
            print("\nStep 1: Scraping website...")
            if not await run_scraper(args.url):
                sys.exit(1)
            
            # Step 2: Text Processing
            print("\nStep 2: Processing and chunking text...")
            if not run_processor():
                sys.exit(1)
            
            # Step 3: Summary Generation
            print("\nStep 3: Generating summaries...")
            if not await run_summarizer(token_limit, args.api_key):
                sys.exit(1)
            
            # Step 4: Combine Summaries
            print("\nStep 4: Combining summaries...")
            if not run_combiner():
                sys.exit(1)
            
            print("\nProcess completed!")
            print("✓ All steps completed successfully")
            print("\nOutput directories:")
            print("- Scraped content: documentation/")
            print("- Text chunks: chunks/")
            print("- Summaries: summaries/")
            if os.path.exists('summaries/optimized'):
                print("- Optimized summaries: summaries/optimized/")
            print("\nOutput files:")
            print("- Combined summary: summaries/combined_summary.txt")
            if os.path.exists('summaries/optimized'):
                print("- Combined optimized summary: summaries/optimized/combined_summary.txt")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 