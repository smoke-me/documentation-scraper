import os
import json
import asyncio
import tiktoken
from openai import AsyncOpenAI
from dotenv import load_dotenv
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

@dataclass
class SummaryTask:
    filename: str
    content: str
    output_path: str
    token_count: int = 0

class GPTSummarizer:
    def __init__(self, input_dir='chunks', output_dir='summaries', max_concurrent=2, target_token_limit=32000, api_key=None):
        load_dotenv()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_concurrent = max_concurrent
        self.target_token_limit = target_token_limit
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Initialize async OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=httpx.AsyncClient(timeout=60.0)
        )
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    async def generate_summary(self, text: str, is_second_stage: bool = False, is_third_stage: bool = False) -> Optional[str]:
        """Generate a concise documentation summary using GPT-4o-mini."""
        try:
            if is_third_stage:
                system_message = (
                    "You are a technical documentation expert tasked with EXTREME summarization. "
                    "Your goal is to create an ultra-compact summary that ONLY includes:\n"
                    "1. Core functionality and usage patterns\n"
                    "2. Critical API endpoints and parameters\n"
                    "3. Essential configuration options\n"
                    "AGGRESSIVELY remove:\n"
                    "- All explanatory text that isn't absolutely necessary\n"
                    "- Background information\n"
                    "- Implementation details\n"
                    "- Examples unless they're the only way to convey usage\n"
                    "- Any word that can be removed without losing core meaning\n"
                    "Be ruthless in condensing - every single character counts."
                )
            elif is_second_stage:
                system_message = (
                    "You are a technical documentation expert focused on extreme summarization. "
                    "Create a highly optimized summary that preserves essential information while "
                    "being as concise as possible. Focus ONLY on:\n"
                    "1. Key functionality and usage\n"
                    "2. Critical parameters and configurations\n"
                    "3. Essential technical details\n"
                    "Remove ALL:\n"
                    "- Explanatory text that isn't crucial\n"
                    "- Redundant information\n"
                    "- Verbose descriptions\n"
                    "- Non-essential examples\n"
                    "Every word must justify its existence."
                )
            else:
                system_message = (
                    "You are a technical documentation expert. Summarize the following text into clear, "
                    "concise documentation format. Focus on key concepts, functionality, and important "
                    "details. Remove any unnecessary verbosity while maintaining technical accuracy. "
                    "Prioritize information about usage and configuration over explanations."
                )

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create an extremely concise summary. Focus on usage, parameters, and configuration. "
                            "Remove all unnecessary words. The summary must be as short as possible while retaining "
                            "critical technical information.\n\n" + text
                        )
                    }
                ],
                temperature=0.3,
                max_tokens=16000
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return None

    async def process_chunk(self, task: SummaryTask, is_second_stage: bool = False):
        """Process a single chunk and save its summary."""
        try:
            summary = await self.generate_summary(task.content, is_second_stage)
            if summary:
                task.token_count = self.count_tokens(summary)
                async with asyncio.Lock():
                    with open(task.output_path, 'w', encoding='utf-8') as f:
                        f.write(summary)
                print(f"✓ Processed {task.filename} ({task.token_count} tokens)")
                return task
        except Exception as e:
            print(f"Error processing {task.filename}: {str(e)}")
        return None

    async def process_batch(self, tasks: List[SummaryTask], is_second_stage: bool = False):
        """Process a batch of chunks concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(task):
            async with semaphore:
                return await self.process_chunk(task, is_second_stage)
        
        return await asyncio.gather(
            *(process_with_semaphore(task) for task in tasks)
        )

    def get_pending_tasks(self, force: bool = False, input_dir: str = None) -> List[SummaryTask]:
        """Get list of chunks that need processing."""
        tasks = []
        dir_to_check = input_dir or self.input_dir
        
        for filename in os.listdir(dir_to_check):
            if filename.endswith('.json' if dir_to_check == self.input_dir else '.txt'):
                input_path = os.path.join(dir_to_check, filename)
                output_filename = f"{filename.replace('.json', '')}_summary.txt"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # Skip if summary exists and not forced
                if os.path.exists(output_path) and not force:
                    continue
                
                # Read content
                with open(input_path, 'r', encoding='utf-8') as f:
                    if dir_to_check == self.input_dir:
                        chunk = json.load(f)
                        content = chunk['text']
                    else:
                        content = f.read()
                
                tasks.append(SummaryTask(
                    filename=filename,
                    content=content,
                    output_path=output_path
                ))
        
        return tasks

    async def optimize_summaries(self):
        """Create optimized second-stage and third-stage summaries if needed."""
        # Get total token count of all summaries
        total_tokens = 0
        summaries = []
        
        for filename in os.listdir(self.output_dir):
            if not filename.endswith('_summary.txt'):
                continue
                
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                token_count = self.count_tokens(content)
                total_tokens += token_count
                summaries.append(SummaryTask(
                    filename=filename,
                    content=content,
                    output_path=filepath,
                    token_count=token_count
                ))
        
        if total_tokens <= self.target_token_limit:
            print(f"Total tokens ({total_tokens}) within limit ({self.target_token_limit})")
            return
        
        print(f"Optimizing summaries: {total_tokens} tokens -> {self.target_token_limit} tokens")
        
        # Sort summaries by token count
        summaries.sort(key=lambda x: x.token_count, reverse=True)
        
        # Calculate optimal batch size based on token counts
        max_input_tokens = 128000  # 4o-mini input limit
        max_output_tokens = 16000  # 4o-mini output limit
        current_batch = []
        current_tokens = 0
        batches = []
        
        for summary in summaries:
            if current_tokens + summary.token_count > max_input_tokens:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [summary]
                current_tokens = summary.token_count
            else:
                current_batch.append(summary)
                current_tokens += summary.token_count
        
        if current_batch:
            batches.append(current_batch)
        
        # Process each batch with second-stage optimization
        optimized_dir = os.path.join(self.output_dir, "optimized")
        if not os.path.exists(optimized_dir):
            os.makedirs(optimized_dir)
        
        second_stage_results = []
        for i, batch in enumerate(batches):
            # Combine summaries in batch
            combined_text = "\n\n---\n\n".join(
                f"# {task.filename}\n{task.content}" for task in batch
            )
            
            # Create task for the batch
            batch_task = SummaryTask(
                filename=f"optimized_batch_{i+1}.txt",
                content=combined_text,
                output_path=os.path.join(optimized_dir, f"optimized_batch_{i+1}.txt")
            )
            
            # Process the batch with second-stage optimization
            result = await self.process_chunk(batch_task, is_second_stage=True)
            if result:
                print(f"✓ Optimized batch {i+1} (second stage): {result.token_count} tokens")
                second_stage_results.append(result)
        
        # Check if we need third-stage optimization
        second_stage_tokens = sum(result.token_count for result in second_stage_results)
        if second_stage_tokens > self.target_token_limit:
            print(f"Second stage still exceeds limit ({second_stage_tokens} tokens). Starting third-stage optimization...")
            
            # Combine all second-stage results
            combined_text = "\n\n---\n\n".join(
                f"# Batch {i+1}\n{task.content}" 
                for i, task in enumerate(second_stage_results)
            )
            
            # Create final optimization task
            final_task = SummaryTask(
                filename="final_optimized_summary.txt",
                content=combined_text,
                output_path=os.path.join(optimized_dir, "final_optimized_summary.txt")
            )
            
            # Process with third-stage optimization
            final_result = await self.process_chunk(final_task, is_third_stage=True)
            if final_result:
                print(f"✓ Final optimization complete: {final_result.token_count} tokens")
        
        print(f"✓ Created optimized summaries in {optimized_dir}/")

    async def process_chunks_async(self, force: bool = False):
        """Process all chunks with concurrent API calls."""
        tasks = self.get_pending_tasks(force)
        if not tasks:
            print("No chunks to process")
            return
        
        print(f"Processing {len(tasks)} chunks...")
        results = await self.process_batch(tasks)
        successful = sum(1 for r in results if r)
        print(f"\nCompleted processing {successful}/{len(tasks)} chunks")
        
        # Run second-stage optimization if needed
        await self.optimize_summaries()

    def process_chunks(self, force: bool = False):
        """Main entry point for processing chunks."""
        asyncio.run(self.process_chunks_async(force))

if __name__ == "__main__":
    # Example usage
    summarizer = GPTSummarizer()
    summarizer.process_chunks() 