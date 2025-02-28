import os
import re
import tiktoken
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class SummarySection:
    title: str
    content: str
    filename: str
    token_count: int = 0

class SummaryCombiner:
    def __init__(self, summaries_dir='summaries', max_tokens=32000):
        self.summaries_dir = summaries_dir
        self.combined_file = 'combined_summary.txt'
        self.optimized_combined_file = 'optimized_combined_summary.txt'
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        return len(self.tokenizer.encode(text))

    def extract_title(self, filename: str) -> str:
        """Extract a clean title from the filename."""
        # Remove _summary.txt and clean up
        title = filename.replace('_summary.txt', '')
        # Convert underscores and hyphens to spaces
        title = re.sub(r'[_-]', ' ', title)
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        return title

    def read_summaries(self, directory: str) -> List[SummarySection]:
        """Read all summaries from a directory."""
        sections = []
        
        if not os.path.exists(directory):
            return sections

        for filename in sorted(os.listdir(directory)):
            if filename.endswith('_summary.txt') and not filename.startswith('combined'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        section = SummarySection(
                            title=self.extract_title(filename),
                            content=content,
                            filename=filename,
                            token_count=self.count_tokens(content)
                        )
                        sections.append(section)
        
        return sections

    def optimize_sections(self, sections: List[SummarySection]) -> List[Tuple[str, List[SummarySection]]]:
        """Group sections intelligently for optimization."""
        # Sort sections by token count
        sections = sorted(sections, key=lambda x: x.token_count, reverse=True)
        
        # Calculate target tokens per batch
        total_tokens = sum(s.token_count for s in sections)
        num_batches = (total_tokens + self.max_tokens - 1) // self.max_tokens
        target_tokens = total_tokens // num_batches if num_batches > 0 else total_tokens

        # Group sections by topic/similarity
        batches = []
        current_batch = []
        current_tokens = 0
        current_topic = None

        for section in sections:
            # Simple topic detection from title
            topic = section.title.split()[0] if section.title else None
            
            # Start new batch if:
            # 1. Current batch is too large
            # 2. Topic changes significantly and current batch is substantial
            if (current_tokens + section.token_count > target_tokens * 1.2) or \
               (current_topic and topic != current_topic and current_tokens > target_tokens * 0.5):
                if current_batch:
                    title = f"Batch {len(batches) + 1}: {current_topic or 'Mixed'} Documentation"
                    batches.append((title, current_batch))
                current_batch = []
                current_tokens = 0
                current_topic = topic
            
            current_batch.append(section)
            current_tokens += section.token_count
            if not current_topic:
                current_topic = topic

        # Add remaining sections
        if current_batch:
            title = f"Batch {len(batches) + 1}: {current_topic or 'Mixed'} Documentation"
            batches.append((title, current_batch))

        return batches

    def combine_summaries(self) -> Dict[str, str]:
        """Combine summaries into a single coherent document."""
        result = {}
        
        # First check for final optimized summary
        optimized_dir = os.path.join(self.summaries_dir, 'optimized')
        final_optimized = os.path.join(optimized_dir, 'final_optimized_summary.txt')
        
        if os.path.exists(final_optimized):
            # Use the final optimized summary directly
            with open(final_optimized, 'r', encoding='utf-8') as f:
                final_content = f.read()
                with open(self.optimized_combined_file, 'w', encoding='utf-8') as out:
                    out.write(final_content)
                result['optimized_combined'] = self.optimized_combined_file
                return result
        
        # Process regular summaries
        sections = self.read_summaries(self.summaries_dir)
        if sections:
            # Calculate total tokens
            total_tokens = sum(section.token_count for section in sections)
            
            combined_text = "# Combined Documentation Summary\n\n"
            for section in sections:
                combined_text += f"## {section.title}\n\n{section.content}\n\n"
            
            # Save combined summary
            with open(self.combined_file, 'w', encoding='utf-8') as f:
                f.write(combined_text.strip())
            result['combined'] = self.combined_file
            
            # Check if optimization is needed
            if total_tokens > self.max_tokens:
                print(f"Total tokens ({total_tokens}) exceed limit ({self.max_tokens}). Using optimized summaries...")
                
                # Try to use second-stage optimized summaries
                optimized_sections = self.read_summaries(optimized_dir)
                if optimized_sections:
                    optimized_text = "# Optimized Documentation Summary\n\n"
                    optimized_tokens = 0
                    
                    # Sort sections by importance (assuming shorter sections are more optimized/important)
                    optimized_sections.sort(key=lambda x: x.token_count)
                    
                    for section in optimized_sections:
                        optimized_tokens += section.token_count
                        if optimized_tokens > self.max_tokens:
                            print(f"Warning: Optimized summary still exceeds token limit ({optimized_tokens}/{self.max_tokens})")
                        optimized_text += f"## {section.title}\n\n{section.content}\n\n"
                    
                    # Save optimized combined summary
                    with open(self.optimized_combined_file, 'w', encoding='utf-8') as f:
                        f.write(optimized_text.strip())
                    result['optimized_combined'] = self.optimized_combined_file
        
        return result

if __name__ == "__main__":
    # Example usage
    combiner = SummaryCombiner()
    combiner.combine_summaries() 