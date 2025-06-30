"""
Concurrent query testing for TextTrove
"""
import threading
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import mindsdb_sdk
    from rich.console import Console
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

console = Console()

def run_concurrent_test():
    """Test concurrent queries to the knowledge base"""
    
    try:
        server = mindsdb_sdk.connect('http://127.0.0.1:47334')
        console.print("[green]✓ Connected to MindsDB[/green]")
        
        kb = server.knowledge_bases.get('texttrove_kb')
        console.print("[green]✓ Found TextTrove Knowledge Base[/green]")
        
    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        return
    
    def run_query(query_id: int, search_term: str):
        """Run a single query"""
        try:
            start_time = time.time()
            results = kb.search(query=search_term, limit=3)
            end_time = time.time()
            
            console.print(f"[cyan]Query {query_id}: '{search_term}' - {len(results)} results in {end_time - start_time:.2f}s[/cyan]")
            
        except Exception as e:
            console.print(f"[red]Query {query_id} failed: {e}[/red]")
    
    # Test queries
    test_queries = [
        "project management",
        "artificial intelligence",
        "cloud computing",
        "cybersecurity",
        "technology trends"
    ]
    
    console.print("[yellow]Starting concurrent query test...[/yellow]")
    
    threads = []
    start_time = time.time()
    
    # Create and start threads
    for i in range(10):  # 10 concurrent queries
        query = test_queries[i % len(test_queries)]
        thread = threading.Thread(target=run_query, args=(i+1, query))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    console.print(f"[green]✓ Completed 10 concurrent queries in {total_time:.2f} seconds[/green]")

if __name__ == "__main__":
    run_concurrent_test()