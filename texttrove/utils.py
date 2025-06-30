"""
Utility functions for TextTrove CLI
"""
import os
import time
from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

from rich.console import Console
from rich.progress import Progress
from rich.spinner import Spinner

console = Console()

def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    Extract text from PDF or text file.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        Optional[str]: Extracted text or None if extraction fails
    """
    try:
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            if PdfReader is None:
                console.print("[yellow]Warning: PDF support not available. Install pypdf: pip install pypdf[/yellow]")
                return None
                
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                text_parts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                return '\n'.join(text_parts)
                
        elif file_path.suffix.lower() in ['.txt', '.md', '.rst']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            console.print(f"[yellow]Warning: Unsupported file type: {file_path.suffix}[/yellow]")
            return None
            
    except Exception as e:
        console.print(f"[red]Error processing {file_path}: {str(e)}[/red]")
        return None

def loading_spinner(task_description: str, duration: float = 2.0):
    """
    Show a loading spinner for a given duration.
    
    Args:
        task_description (str): Description of the task
        duration (float): Duration in seconds
    """
    with console.status(f"[cyan]{task_description}...", spinner="dots"):
        time.sleep(duration)

def loading_progress(task_description: str, total: int = 100, duration: float = 2.0):
    """
    Show a progress bar for a given duration.
    
    Args:
        task_description (str): Description of the task
        total (int): Total progress steps
        duration (float): Duration in seconds
    """
    with Progress() as progress:
        task_id = progress.add_task(f"[cyan]{task_description}...", total=total)
        step_duration = duration / total
        
        for _ in range(total):
            progress.update(task_id, advance=1)
            time.sleep(step_duration)

def get_banner() -> str:
    """
    Load and return the ASCII banner.
    
    Returns:
        str: ASCII banner text
    """
    try:
        banner_path = Path(__file__).parent / "assets" / "banner.txt"
        with open(banner_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
 _____         _  _____                    
|_   _|       | ||_   _|                   
  | | _____  _| |_ | |_ __ ___ __   _____   
  | |/ _ \\ \\/ / __|| | '__/ _ \\\\ \\ / / _ \\  
  | |  __/>  <| |_ | | | | (_) \\ V /  __/  
  \\_/\\___/_/\\_\\\\__\\\\_/|_|  \\___/ \\_/ \\___|  
                                           
      🔍 Search Smarter, Summarize Faster 🚀
"""

def validate_folder(folder_path: str) -> bool:
    """
    Validate if folder exists and contains files.
    
    Args:
        folder_path (str): Path to the folder
        
    Returns:
        bool: True if valid, False otherwise
    """
    path = Path(folder_path)
    if not path.exists():
        console.print(f"[red]Error: Folder {folder_path} does not exist[/red]")
        return False
    
    if not path.is_dir():
        console.print(f"[red]Error: {folder_path} is not a directory[/red]")
        return False
    
    # Check for supported files
    supported_extensions = ['.txt', '.pdf', '.md', '.rst']
    files = [f for f in path.iterdir() if f.suffix.lower() in supported_extensions]
    
    if not files:
        console.print(f"[yellow]Warning: No supported files found in {folder_path}[/yellow]")
        console.print(f"[yellow]Supported formats: {', '.join(supported_extensions)}[/yellow]")
        return False
    
    return True