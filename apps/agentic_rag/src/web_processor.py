from pathlib import Path
import json
import argparse
from typing import List, Dict, Any
from trafilatura import fetch_url, extract, extract_metadata
from urllib.parse import urlparse

def is_url(string: str) -> bool:
    """Check if a string is a valid URL"""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_domain(url: str) -> str:
    """Extract domain from URL"""
    parsed = urlparse(url)
    return parsed.netloc.lower()

class WebProcessor:
    def __init__(self, chunk_size: int = 500):
        """Initialize web processor with chunk size"""
        self.chunk_size = chunk_size
        # Define domains that need special handling
        self.special_domains = {
            'x.com': 'twitter',
            'twitter.com': 'twitter',
            'github.com': 'github'
        }
    
    def _handle_twitter(self, url: str) -> Dict[str, Any]:
        """Special handling for Twitter/X URLs"""
        # Extract tweet ID from URL
        tweet_id = url.split('/')[-1]
        return {
            'text': f"Twitter/X content (Tweet ID: {tweet_id}). Note: Twitter content cannot be directly extracted. Please visit {url} to view the content.",
            'metadata': {
                'source': url,
                'type': 'twitter',
                'tweet_id': tweet_id
            }
        }
    
    def _handle_github(self, url: str) -> Dict[str, Any]:
        """Special handling for GitHub URLs"""
        # Extract repo info from URL
        parts = url.split('/')
        if len(parts) >= 5:
            owner = parts[3]
            repo = parts[4]
            return {
                'text': f"GitHub Repository: {owner}/{repo}. This is a GitHub repository. For better results, try accessing specific files or the README directly.",
                'metadata': {
                    'source': url,
                    'type': 'github',
                    'owner': owner,
                    'repo': repo
                }
            }
        return None

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of roughly equal size"""
        # Split into sentences (roughly)
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            # Add period back
            sentence = sentence + '.'
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        # Add any remaining text
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def process_url(self, url: str) -> List[Dict[str, Any]]:
        """Process a URL and return chunks of text with metadata"""
        try:
            domain = get_domain(url)
            
            # Check if this domain needs special handling
            if domain in self.special_domains:
                handler = getattr(self, f"_handle_{self.special_domains[domain]}", None)
                if handler:
                    result = handler(url)
                    if result:
                        return [{
                            "text": result["text"],
                            "metadata": result["metadata"]
                        }]
            
            # Standard processing for other domains
            downloaded = fetch_url(url)
            if not downloaded:
                raise ValueError(f"Failed to fetch URL: {url}")
            
            # Extract text and metadata
            text = extract(downloaded, include_comments=False, include_tables=False)
            try:
                metadata = extract_metadata(downloaded)
                # Convert metadata to dict if it's not already
                if not isinstance(metadata, dict):
                    metadata = {
                        'title': getattr(metadata, 'title', ''),
                        'author': getattr(metadata, 'author', ''),
                        'date': getattr(metadata, 'date', ''),
                        'sitename': getattr(metadata, 'sitename', ''),
                        'categories': getattr(metadata, 'categories', []),
                        'tags': getattr(metadata, 'tags', [])
                    }
            except Exception as e:
                print(f"Warning: Metadata extraction failed: {str(e)}")
                metadata = {}
            
            if not text:
                raise ValueError(f"No text content extracted from URL: {url}. This might be due to:\n" +
                               "1. Website blocking automated access\n" +
                               "2. Content requiring JavaScript\n" +
                               "3. Content behind authentication\n" +
                               "4. Website using non-standard HTML structure")
            
            # Split into chunks
            text_chunks = self._chunk_text(text)
            
            # Process chunks into a standardized format
            processed_chunks = []
            for i, chunk in enumerate(text_chunks):
                processed_chunk = {
                    "text": chunk,
                    "metadata": {
                        "source": url,
                        "title": metadata.get('title', ''),
                        "author": metadata.get('author', ''),
                        "date": metadata.get('date', ''),
                        "sitename": metadata.get('sitename', ''),
                        "categories": metadata.get('categories', []),
                        "tags": metadata.get('tags', []),
                        "chunk_id": i,
                        "type": "webpage"
                    }
                }
                processed_chunks.append(processed_chunk)
            
            return processed_chunks
        
        except Exception as e:
            raise Exception(f"Error processing URL {url}: {str(e)}")
    
    def process_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Process multiple URLs and return combined chunks"""
        all_chunks = []
        
        for url in urls:
            try:
                chunks = self.process_url(url)
                all_chunks.extend(chunks)
                print(f"✓ Processed {url}")
            except Exception as e:
                print(f"✗ Failed to process {url}: {str(e)}")
        
        return all_chunks

def main():
    parser = argparse.ArgumentParser(description="Process web pages and extract text chunks")
    parser.add_argument("--input", required=True, help="Input URL or file containing URLs (one per line)")
    parser.add_argument("--output", required=True, help="Output JSON file for chunks")
    parser.add_argument("--chunk-size", type=int, default=500, help="Maximum size of text chunks")
    
    args = parser.parse_args()
    processor = WebProcessor(chunk_size=args.chunk_size)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if is_url(args.input):
            print(f"\nProcessing URL: {args.input}")
            print("=" * 50)
            chunks = processor.process_url(args.input)
        else:
            # Read URLs from file
            with open(args.input, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            print(f"\nProcessing {len(urls)} URLs from: {args.input}")
            print("=" * 50)
            chunks = processor.process_urls(urls)
        
        # Save chunks to JSON
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print("\nSummary:")
        print(f"✓ Processed {len(chunks)} chunks")
        print(f"✓ Saved to {args.output}")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 