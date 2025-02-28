import os
import re
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SummarySection:
    title: str
    content: str
    filename: str

class SummaryCombiner:
    def __init__(self, summaries_dir='summaries'):
        self.summaries_dir = summaries_dir
        self.combined_file = os.path.join(summaries_dir, 'combined_summary.txt')
        self.optimized_combined_file = os.path.join(summaries_dir, 'optimized', 'combined_summary.txt')

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
            if filename.endswith('_summary.txt') and filename != 'combined_summary.txt':
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        sections.append(SummarySection(
                            title=self.extract_title(filename),
                            content=content,
                            filename=filename
                        ))
        
        return sections

    def combine_summaries(self) -> Dict[str, str]:
        """Combine summaries into a single coherent document."""
        result = {}
        
        # Process regular summaries
        sections = self.read_summaries(self.summaries_dir)
        if sections:
            combined_text = "# Combined Documentation Summary\n\n"
            for section in sections:
                combined_text += f"## {section.title}\n\n{section.content}\n\n"
            
            # Save combined summary
            os.makedirs(self.summaries_dir, exist_ok=True)
            with open(self.combined_file, 'w', encoding='utf-8') as f:
                f.write(combined_text.strip())
            result['combined'] = self.combined_file
        
        # Process optimized summaries if they exist
        optimized_dir = os.path.join(self.summaries_dir, 'optimized')
        if os.path.exists(optimized_dir):
            sections = self.read_summaries(optimized_dir)
            if sections:
                combined_text = "# Combined Optimized Documentation Summary\n\n"
                for section in sections:
                    combined_text += f"## {section.title}\n\n{section.content}\n\n"
                
                # Save combined optimized summary
                os.makedirs(optimized_dir, exist_ok=True)
                with open(self.optimized_combined_file, 'w', encoding='utf-8') as f:
                    f.write(combined_text.strip())
                result['optimized_combined'] = self.optimized_combined_file
        
        return result

if __name__ == "__main__":
    # Example usage
    combiner = SummaryCombiner()
    combiner.combine_summaries() 