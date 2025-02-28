import os
import json
import tiktoken
from concurrent.futures import ThreadPoolExecutor
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Section:
    title: str
    content: str
    level: int
    token_count: int

class TextProcessor:
    def __init__(self, input_dir='documentation', max_tokens=16000):
        self.input_dir = input_dir
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.content_hashes = set()
        print(f"Initializing text processor with max_tokens={max_tokens}")

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))

    def clean_metadata(self, text: str) -> Tuple[str, str]:
        """Clean metadata from the text and return the URL and cleaned text."""
        url = ""
        cleaned_text = text
        
        # Extract and remove URL
        url_match = re.match(r'URL: (.*?)\n', text)
        if url_match:
            url = url_match.group(1)
            cleaned_text = text[len(url_match.group(0)):].strip()
        
        # Remove token count line if present
        token_count_match = re.match(r'Token Count: \d+\n\n', cleaned_text)
        if token_count_match:
            cleaned_text = cleaned_text[len(token_count_match.group(0)):].strip()
        
        return url, cleaned_text

    def extract_sections(self, text: str, filename: str) -> List[Section]:
        """Extract hierarchical sections from text based on headers or content blocks."""
        lines = text.split('\n')
        sections = []
        current_section = None
        current_content = []
        
        # More flexible header pattern that includes both Markdown and other common headers
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$|^([A-Z][A-Za-z0-9\s]{2,50})$')
        
        for line in lines:
            header_match = header_pattern.match(line)
            
            if header_match:
                # Save previous section if it exists
                if current_section is not None:
                    content = '\n'.join(current_content).strip()
                    if content:
                        sections.append(Section(
                            title=current_section[1],
                            content=content,
                            level=current_section[0],
                            token_count=self.count_tokens(content)
                        ))
                
                # Start new section
                if header_match.group(1):  # Markdown header
                    level = len(header_match.group(1))
                    title = header_match.group(2)
                else:  # Plain text header
                    level = 1
                    title = header_match.group(3)
                
                current_section = (level, title)
                current_content = []
            else:
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            content = '\n'.join(current_content).strip()
            if content:
                sections.append(Section(
                    title=current_section[1],
                    content=content,
                    level=current_section[0],
                    token_count=self.count_tokens(content)
                ))
        
        # If no sections were found, create one from the entire content
        if not sections and text.strip():
            content = text.strip()
            sections.append(Section(
                title=os.path.splitext(filename)[0],
                content=content,
                level=1,
                token_count=self.count_tokens(content)
            ))
        
        return sections

    def optimize_chunk_content(self, content: str) -> str:
        """Optimize content for LLM processing."""
        # Remove redundant whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove duplicate punctuation
        content = re.sub(r'([.!?])\1+', r'\1', content)
        
        # Remove common redundant phrases
        redundant_phrases = [
            r'as mentioned earlier',
            r'as discussed above',
            r'as we can see',
            r'it is worth noting that',
            r'it should be noted that',
            r'it is important to note that'
        ]
        for phrase in redundant_phrases:
            content = re.sub(phrase, '', content, flags=re.IGNORECASE)
        
        return content.strip()

    def create_intelligent_chunks(self, sections: List[Section], source_file: str) -> List[Dict]:
        """Create optimized chunks from sections while preserving context."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for section in sections:
            section_total = section.token_count + 50  # Add buffer for formatting
            
            # If section alone exceeds max tokens, split it
            if section_total > self.max_tokens:
                if current_chunk:
                    chunk_text = self.build_chunk_text(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'source': source_file,
                        'token_count': current_tokens
                    })
                    current_chunk = []
                    current_tokens = 0
                
                # Split large section into smaller chunks
                words = section.content.split()
                current_part = []
                current_part_tokens = 0
                
                for word in words:
                    word_tokens = self.count_tokens(word + ' ')
                    if current_part_tokens + word_tokens > self.max_tokens - 100:
                        # Save current part
                        content = ' '.join(current_part)
                        chunks.append({
                            'text': f"# {section.title} (continued)\n\n{content}",
                            'source': source_file,
                            'token_count': current_part_tokens
                        })
                        current_part = []
                        current_part_tokens = 0
                    
                    current_part.append(word)
                    current_part_tokens += word_tokens
                
                # Add remaining part if any
                if current_part:
                    content = ' '.join(current_part)
                    chunks.append({
                        'text': f"# {section.title} (continued)\n\n{content}",
                        'source': source_file,
                        'token_count': current_part_tokens
                    })
                
            # If section fits in current chunk
            elif current_tokens + section_total <= self.max_tokens:
                current_chunk.append(section)
                current_tokens += section_total
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunk_text = self.build_chunk_text(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'source': source_file,
                        'token_count': current_tokens
                    })
                
                current_chunk = [section]
                current_tokens = section_total
        
        # Add the last chunk
        if current_chunk:
            chunk_text = self.build_chunk_text(current_chunk)
            chunks.append({
                'text': chunk_text,
                'source': source_file,
                'token_count': current_tokens
            })
        
        return chunks

    def build_chunk_text(self, sections: List[Section]) -> str:
        """Build formatted text from sections."""
        chunk_parts = []
        for section in sections:
            header = '#' * section.level
            chunk_parts.append(f"{header} {section.title}")
            chunk_parts.append(section.content)
        
        text = '\n\n'.join(chunk_parts)
        return self.optimize_chunk_content(text)

    def process_file(self, filepath: str) -> List[Dict]:
        """Process a single file."""
        try:
            print(f"Processing {filepath}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Clean metadata and get URL
            url, cleaned_text = self.clean_metadata(text)
            
            # Extract sections
            filename = os.path.basename(filepath)
            sections = self.extract_sections(cleaned_text, filename)
            
            if not sections:
                print(f"Warning: No sections found in {filepath}")
                return []
            
            chunks = self.create_intelligent_chunks(sections, filename)
            print(f"✓ Generated {len(chunks)} chunks from {filepath}")
            return chunks
            
        except Exception as e:
            print(f"Error processing {filepath}: {str(e)}")
            return []

    def process_files(self) -> List[Dict]:
        """Process all files in parallel."""
        all_chunks = []
        files = [f for f in os.listdir(self.input_dir) if f.endswith('.txt')]
        
        if not files:
            print(f"No .txt files found in {self.input_dir}/")
            return []
        
        print(f"Found {len(files)} files to process")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.process_file, os.path.join(self.input_dir, f))
                for f in files
            ]
            
            for future in futures:
                chunks = future.result()
                all_chunks.extend(chunks)
        
        print(f"Generated {len(all_chunks)} total chunks")
        return all_chunks

    def save_chunks(self, chunks: List[Dict], output_dir='chunks'):
        """Save chunks to individual files."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if not chunks:
            print("No chunks to save")
            return
        
        # Group chunks by source file
        chunks_by_source = defaultdict(list)
        for i, chunk in enumerate(chunks):
            chunks_by_source[chunk['source']].append((i, chunk))
        
        # Save chunks with meaningful names
        saved_count = 0
        for source, source_chunks in chunks_by_source.items():
            for i, (_, chunk) in enumerate(source_chunks):
                base_name = os.path.splitext(source)[0]
                chunk_filename = f"{base_name}_part_{i+1}.json"
                filepath = os.path.join(output_dir, chunk_filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, indent=2)
                saved_count += 1
        
        print(f"✓ Saved {saved_count} chunks to {output_dir}/")

if __name__ == "__main__":
    # Example usage
    processor = TextProcessor()
    chunks = processor.process_files()
    processor.save_chunks(chunks) 