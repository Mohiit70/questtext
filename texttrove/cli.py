import sys
import datetime
from pathlib import Path
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.append(str(Path(__file__).parent.parent))

try:
    import mindsdb_sdk
except ImportError:
    print("Error: mindsdb-sdk not installed. Run: pip install mindsdb-sdk")
    sys.exit(1)

from texttrove.utils import (
    extract_text_from_file,
    loading_spinner,
    get_banner,
    validate_folder,
    console
)

app = typer.Typer(
    name="texttrove",
    help="🔍 TextTrove CLI - Search Smarter, Summarize Faster",
    add_completion=False
)

server = None
config = {}

def load_config():
    global config
    config_path = Path("config.yaml")
    if not config_path.exists():
        create_default_config()
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

def create_default_config():
    default_config = {
        'ai_provider': 'groq',
        'groq_api_key': '',
        'mindsdb_url': 'http://127.0.0.1:47334',
        'kb_name': 'texttrove_kb',
        'ollama_url': 'http://localhost:11434',
        'ollama_model': 'llama3',
        'embedding_model': 'nomic-embed-text',
        'embedding_provider': 'ollama',
        'huggingface_api_token': ''
    }
    with open('config.yaml', 'w') as f:
        yaml.dump(default_config, f)
    console.print("[green]Created default config.yaml. Please update it with your settings.[/green]")

def connect_to_mindsdb():
    global server
    try:
        server = mindsdb_sdk.connect(config.get('mindsdb_url'))
        console.print(f"[green]✓ Connected to MindsDB at {config.get('mindsdb_url')}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to connect to MindsDB: {e}[/red]")
        sys.exit(1)

def show_banner():
    banner = get_banner()
    console.print(Panel(banner, style="bold green", title="TextTrove CLI"))

@app.callback()
def main():
    load_config()
    connect_to_mindsdb()

@app.command()
def ingest(folder: str, kb_name: str = typer.Option(None, "--kb-name", "-k"), category: str = typer.Option("general", "--category", "-c")):
    show_banner()
    if not validate_folder(folder):
        raise typer.Exit(1)

    kb_name = kb_name or config.get('kb_name', 'texttrove_kb')
    embedding_model = config.get('embedding_model', 'nomic-embed-text')
    embedding_provider = config.get('embedding_provider', 'ollama')

    loading_spinner("Initializing Knowledge Base", 1.5)

    try:
        try:
            kb = server.knowledge_bases.get(kb_name)
            console.print(f"[blue]Using existing Knowledge Base: {kb_name}[/blue]")
        except:
            embedding_model_config = {
                "model_name": embedding_model,
                "provider": embedding_provider
            }
            kb = server.knowledge_bases.create(
                name=kb_name,
                embedding_model=embedding_model_config
            )
            console.print(f"[green]Created new Knowledge Base: {kb_name}[/green]")

        folder_path = Path(folder)
        files_processed = 0
        files_failed = 0

        supported_files = [f for f in folder_path.iterdir() if f.suffix.lower() in ['.txt', '.pdf', '.md', '.rst']]
        if not supported_files:
            console.print("[yellow]No supported files found![/yellow]")
            raise typer.Exit(1)

        console.print(f"[cyan]Processing {len(supported_files)} files...[/cyan]")

        for file_path in supported_files:
            try:
                content = extract_text_from_file(file_path)
                if content and content.strip():
                    kb.insert([{
                        'content': content,
                        'metadata': {
                            'category': category,
                            'date_added': str(datetime.date.today()),
                            'source': file_path.name,
                            'file_type': file_path.suffix.lower()
                        }
                    }])
                    files_processed += 1
                    console.print(f"[green]✓ Processed: {file_path.name}[/green]")
                else:
                    files_failed += 1
                    console.print(f"[yellow]⚠ Skipped (empty): {file_path.name}[/yellow]")
            except Exception as e:
                files_failed += 1
                console.print(f"[red]✗ Failed: {file_path.name} - {str(e)}[/red]")

        summary_table = Table(title="Ingestion Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="green")
        summary_table.add_row("Files Processed", str(files_processed))
        summary_table.add_row("Files Failed", str(files_failed))
        summary_table.add_row("Knowledge Base", kb_name)
        summary_table.add_row("Category", category)

        console.print(summary_table)

    except Exception as e:
        console.print(f"[red]Error during ingestion: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def query(search: str, kb_name: str = typer.Option(None, "--kb-name", "-k"), limit: int = typer.Option(5, "--limit", "-l")):
    show_banner()
    kb_name = kb_name or config.get('kb_name', 'texttrove_kb')
    loading_spinner("Searching Knowledge Base", 1.0)

    try:
        kb = server.knowledge_bases.get(kb_name)
        results = kb.search(query=search, limit=limit)
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        console.print(f"[green]Found {len(results)} results for: '{search}'[/green]\n")
        for i, result in enumerate(results, 1):
            content = result.get('content', '')[:300] + "..." if len(result.get('content', '')) > 300 else result.get('content', '')
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            console.print(Panel(f"[bold cyan]Source:[/bold cyan] {source}\n\n{content}", title=f"Result {i}", style="blue"))

    except AttributeError as e:
        console.print(f"[red]Error: KnowledgeBase does not support this operation. Ensure MindsDB SDK is up-to-date and the knowledge base exists: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during search: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def summarize(search: str, kb_name: str = typer.Option(None, "--kb-name", "-k")):
    show_banner()
    kb_name = kb_name or config.get('kb_name', 'texttrove_kb')
    loading_spinner("Generating summary", 2.0)

    try:
        kb = server.knowledge_bases.get(kb_name)
        results = kb.search(query=search, limit=3)
        if not results:
            console.print("[yellow]No results to summarize.[/yellow]")
            return

        combined_text = '\n\n'.join([r['content'][:500] for r in results])
        provider = config.get('ai_provider')

        if provider == 'groq':
            summary = summarize_with_groq(combined_text)
        else:
            summary = summarize_with_ollama(combined_text)

        console.print(Panel(f"[cyan]Query:[/cyan] {search}\n\n[green]Summary:[/green]\n{summary}", title="📝 AI Summary", style="cyan"))

    except AttributeError as e:
        console.print(f"[red]Error: KnowledgeBase does not support this operation. Ensure MindsDB SDK is up-to-date and the knowledge base exists: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during summarization: {e}[/red]")
        raise typer.Exit(1)

def summarize_with_groq(text: str) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=config.get('groq_api_key'))
        if not config.get('groq_api_key'):
            return "Error: Groq API key not configured in config.yaml"
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": f"Summarize this:\n\n{text}"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error with Groq: {e}"

def summarize_with_ollama(text: str) -> str:
    try:
        import ollama
        client = ollama.Client(host=config.get('ollama_url'))
        model = config.get('ollama_model', 'llama3')
        prompt = f"Summarize this:\n\n{text}"
        response = client.generate(model=model, prompt=prompt)
        return response['response']
    except Exception as e:
        return f"Error with Ollama: {e}"

if __name__ == "__main__":
    app()