from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
import argparse
from urllib.parse import urlparse
import uuid
from gitingest import ingest

def is_github_url(url: str) -> bool:
    """Check if a string is a valid GitHub URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() == "github.com"
    except Exception:
        return False

def extract_repo_name(repo_path: str) -> str:
    """Extract repository name from path or URL"""
    if is_github_url(repo_path):
        # For GitHub URLs, extract owner/repo format
        parts = repo_path.rstrip('/').split('/')
        if len(parts) >= 5:
            return f"{parts[3]}/{parts[4]}"  # owner/repo format
    
    # For local paths, use the last directory name
    return Path(repo_path).name

class RepoProcessor:
    def __init__(self, chunk_size: int = 500):
        """Initialize repository processor with chunk size"""
        self.chunk_size = chunk_size
    
    def _extract_metadata(self, summary: Dict[str, Any], tree: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """Extract metadata from repository summary and tree"""
        # Extract repo name from path or URL
        repo_name = extract_repo_name(repo_path)
        
        # Handle case where summary might be a string
        if isinstance(summary, str):
            return {
                "repo_name": repo_name,
                "file_count": len(tree) if tree else 0
            }
        
        return {
            "repo_name": repo_name,  # Use extracted name instead of summary
            "file_count": len(tree) if tree else 0
        }
    
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
    
    def process_repo(self, repo_path: str | Path) -> Tuple[List[Dict[str, Any]], str]:
        """Process a repository and return chunks of text with metadata"""
        try:
            # Generate a unique document ID
            document_id = str(uuid.uuid4())
            
            # Check if it's a GitHub URL
            if isinstance(repo_path, str) and is_github_url(repo_path):
                print(f"Processing GitHub repository: {repo_path}")
            else:
                print(f"Processing local repository: {repo_path}")
            
            # Ingest repository
            summary, tree, content = ingest(str(repo_path))
            
            # Extract metadata
            metadata = self._extract_metadata(summary, tree, str(repo_path))
            
            # Process content into chunks
            processed_chunks = []
            chunk_id = 0
            
            if isinstance(content, dict):
                # Handle dictionary of file contents
                for file_path, file_content in content.items():
                    if isinstance(file_content, str) and file_content.strip():  # Only process non-empty content
                        # Split content into chunks
                        text_chunks = self._chunk_text(file_content)
                        
                        for text_chunk in text_chunks:
                            chunk = {
                                "text": text_chunk,
                                "metadata": {
                                    **metadata,
                                    "source": str(repo_path),
                                    "document_id": document_id,
                                    "chunk_id": chunk_id
                                }
                            }
                            processed_chunks.append(chunk)
                            chunk_id += 1
            elif isinstance(content, str):
                # Handle single string content
                text_chunks = self._chunk_text(content)
                
                for text_chunk in text_chunks:
                    chunk = {
                        "text": text_chunk,
                        "metadata": {
                            **metadata,
                            "source": str(repo_path),
                            "document_id": document_id,
                            "chunk_id": chunk_id
                        }
                    }
                    processed_chunks.append(chunk)
                    chunk_id += 1
            
            return processed_chunks, document_id
        
        except Exception as e:
            raise Exception(f"Error processing repository {repo_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Process GitHub repositories and extract content")
    parser.add_argument("--input", required=True, 
                       help="Input repository path or GitHub URL")
    parser.add_argument("--output", required=True, help="Output JSON file for chunks")
    parser.add_argument("--chunk-size", type=int, default=500,
                       help="Maximum size of text chunks")
    
    args = parser.parse_args()
    processor = RepoProcessor(chunk_size=args.chunk_size)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nProcessing repository: {args.input}")
        print("=" * 50)
        
        chunks, doc_id = processor.process_repo(args.input)
        
        # Save chunks to JSON
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print("\nSummary:")
        print(f"✓ Processed {len(chunks)} chunks")
        print(f"✓ Document ID: {doc_id}")
        print(f"✓ Saved to {args.output}")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 