"""
Document ingestion performance testing for TextTrove
"""
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import mindsdb_sdk
    from rich.console import Console
    from texttrove.utils import extract_text_from_file
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

console = Console()

def run_ingestion_test():
    """Test document ingestion performance"""
    
    try:
        server = mindsdb_sdk.connect('http://127.0.0.1:47334')
        console.print("[green]✓ Connected to MindsDB[/green]")
        
        # Create test KB
        test_kb_name = 'texttrove_test_kb'
        try:
            kb = server.knowledge_bases.get(test_kb_name)
            console.print(f"[blue]Using existing test KB: {test_kb_name}[/blue]")
        except:
            kb = server.knowledge_bases.create(
                name=test_kb_name,
                model='sentence_transformers'
            )
            console.print(f"[green]✓ Created test KB: {test_kb_name}[/green]")
        
    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        return
    
    # Test with sample documents
    sample_docs_path = Path("sample_docs")
    if not sample_docs_path.exists():
        console.print("[red]sample_docs folder not found[/red]")
        return
    
    files = list(sample_docs_path.glob("*.txt"))
    if not files:
        console.print("[red]No .txt files found in sample_docs[/red]")
        return
    
    console.print(f"[yellow]Testing ingestion with {len(files)} documents...[/yellow]")
    
    start_time = time.time()
    processed_count = 0
    
    for file_path in files:
        try:
            content = extract_text_from_file(str(file_path))
            if content and content.strip():
                kb.insert([{
                    'content': content,
                    'metadata': {
                        'source': file_path.name,
                        'test_run': True,
                        'ingestion_time': time.time()
                    }
                }])
                processed_count += 1
                console.print(f"[cyan]✓ Processed: {file_path.name}[/cyan]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed: {file_path.name} - {str(e)}[/red]")
    
    total_time = time.time() - start_time
    console.print(f"[green]✓ Ingested {processed_count} documents in {total_time:.2f} seconds[/green]")
    console.print(f"[blue]Average time per document: {total_time/max(processed_count, 1):.2f} seconds[/blue]")

if __name__ == "__main__":
    run_ingestion_test()