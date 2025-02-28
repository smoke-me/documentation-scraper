import os
import time
import asyncio
import aiohttp
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
import langdetect
from collections import defaultdict
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
import tiktoken

class WebScraper:
    def __init__(self, base_url, output_dir='documentation', max_concurrent_requests=4):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.base_path = urlparse(base_url).path
        self.visited_urls = set()
        self.output_dir = output_dir
        self.max_concurrent_requests = max_concurrent_requests
        self.content_hashes = set()  # For deduplication
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.success_count = 0  # Track successful scrapes
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def is_valid_url(self, url):
        """Check if URL belongs to the same domain and documentation path."""
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != self.domain:
            return False
            
        # Must be within the same documentation path
        if not parsed.path.startswith(self.base_path):
            return False
            
        # Exclude non-documentation file types and common unwanted paths
        excluded_patterns = (
            '.pdf', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.css', '.js',
            '/assets/', '/images/', '/static/', '/search', '/login', '/signup',
            '/api/v', '/download', '/archive'
        )
        if any(pattern in url.lower() for pattern in excluded_patterns):
            return False
            
        return True

    def clean_text(self, text):
        """Clean and normalize text content."""
        # Remove multiple newlines and spaces
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove code block markers but keep the content
        text = re.sub(r'```\w*\n', '', text)
        text = text.replace('```', '')
        
        return text.strip()

    def is_english_content(self, text):
        """Check if content is primarily in English."""
        try:
            return langdetect.detect(text) == 'en'
        except:
            return True  # Default to True if detection fails

    def get_content_hash(self, text):
        """Generate hash of text content for deduplication."""
        return hashlib.md5(text.encode()).hexdigest()

    def is_duplicate_content(self, text):
        """Check if content is duplicate based on hash."""
        content_hash = self.get_content_hash(text)
        if content_hash in self.content_hashes:
            return True
        self.content_hashes.add(content_hash)
        return False

    def extract_text(self, soup):
        """Extract meaningful text from the webpage with intelligent filtering."""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Extract text from remaining elements
        content_elements = []
        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'pre', 'code']):
            text = element.get_text().strip()
            if text and len(text) > 50:  # Skip very short snippets
                content_elements.append(text)

        text = '\n'.join(content_elements)
        return self.clean_text(text)

    def get_title(self, soup, url):
        """Extract and clean page title."""
        title = soup.title.string if soup.title else None
        if not title:
            title = url.rstrip('/').split('/')[-1]
        
        # Clean title for filename
        title = re.sub(r'[<>:"/\\|?*\xa0]', '_', title)
        title = ''.join(char for char in title if char.isprintable())
        title = title.strip()
        
        if not title or title.isspace():
            title = "untitled"
        return title[:100]

    async def scrape_site(self):
        """Scrape the entire website asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                to_visit = [self.base_url]
                while to_visit:
                    # Process multiple URLs concurrently
                    tasks = []
                    for _ in range(min(self.max_concurrent_requests, len(to_visit))):
                        if not to_visit:
                            break
                        url = to_visit.pop(0)
                        if url not in self.visited_urls:
                            self.visited_urls.add(url)
                            tasks.append(self.scrape_page(session, url))
                    
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for result in results:
                            if isinstance(result, Exception):
                                print(f"Error during scraping: {str(result)}")
                                continue
                            if result:  # Only extend if we got valid links
                                new_links = [link for link in result if link not in self.visited_urls]
                                to_visit.extend(new_links)
                    
                    # Small delay to be nice to the server
                    await asyncio.sleep(0.1)
            
            if self.success_count == 0:
                raise Exception("No content was successfully scraped")
            
            print(f"Successfully scraped {self.success_count} pages")
            
        except Exception as e:
            print(f"Error during scraping process: {str(e)}")
            raise  # Re-raise the exception to be caught by main.py

    async def scrape_page(self, session, url):
        """Scrape a single page asynchronously."""
        try:
            async with self.semaphore:  # Limit concurrent requests
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        print(f"Failed to fetch {url}: HTTP {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract and clean text
                    text = self.extract_text(soup)
                    
                    # Skip if not primarily English or duplicate
                    if not text or not self.is_english_content(text) or self.is_duplicate_content(text):
                        return []
                    
                    # Save content if it's substantial
                    token_count = len(self.encoding.encode(text))
                    if token_count > 100:  # Skip very small content
                        title = self.get_title(soup, url)
                        filename = f"{title}.txt"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(f"URL: {url}\n")
                            f.write(f"Token Count: {token_count}\n\n")
                            f.write(text)
                        
                        self.success_count += 1
                        print(f"✓ Scraped {url} ({token_count} tokens)")
                    
                    # Find all links
                    links = []
                    for link in soup.find_all('a'):
                        href = link.get('href')
                        if href:
                            full_url = urljoin(url, href)
                            if self.is_valid_url(full_url):
                                links.append(full_url)
                    
                    return links
                    
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []

    def run(self):
        """Run the scraper with asyncio."""
        asyncio.run(self.scrape_site())

if __name__ == "__main__":
    # Example usage
    scraper = WebScraper("https://example.com")
    scraper.run() 