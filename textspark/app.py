"""
TextSpark Web Application - Optional web interface for TextTrove
"""
import os
import sys
import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from flask import Flask, request, render_template, flash, redirect, url_for
    import mindsdb_sdk
    import yaml
    from texttrove.utils import extract_text_from_file
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Load configuration
def load_config():
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {'mindsdb_url': 'http://127.0.0.1:47334', 'kb_name': 'texttrove_kb'}

config = load_config()

# Connect to MindsDB
try:
    server = mindsdb_sdk.connect(config.get('mindsdb_url', 'http://127.0.0.1:47334'))
except Exception as e:
    print(f"Failed to connect to MindsDB: {e}")
    server = None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page with search functionality"""
    results = []
    summary = ""
    
    if request.method == 'POST' and server:
        search_query = request.form.get('search', '').strip()
        category_filter = request.form.get('category', '').strip()
        
        if search_query:
            try:
                kb_name = config.get('kb_name', 'texttrove_kb')
                kb = server.knowledge_bases.get(kb_name)
                
                # Perform search
                results = kb.search(query=search_query, limit=5)
                
                if results:
                    # Generate simple summary
                    combined_content = []
                    for result in results[:3]:  # Use top 3 results
                        content = result.get('content', '')
                        if content:
                            combined_content.append(content[:200])
                    
                    if combined_content:
                        summary = f"Found {len(results)} results related to '{search_query}'. "
                        summary += "Key topics include information from " + ", ".join([
                            result.get('metadata', {}).get('source', 'unknown source') 
                            for result in results[:3]
                        ])
                
                flash(f"Found {len(results)} results for '{search_query}'", "success")
                
            except Exception as e:
                flash(f"Search error: {str(e)}", "error")
        else:
            flash("Please enter a search query", "warning")
    
    return render_template('index.html', results=results, summary=summary)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload"""
    if not server:
        flash("MindsDB connection not available", "error")
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash("No file selected", "error")
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash("No file selected", "error")
        return redirect(url_for('index'))
    
    try:
        # Extract text from uploaded file
        if file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
        elif file.filename.endswith('.pdf'):
            # Save temporarily and extract
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)
            content = extract_text_from_file(temp_path)
            os.remove(temp_path)
        else:
            flash("Unsupported file type. Please upload .txt or .pdf files", "error")
            return redirect(url_for('index'))
        
        if not content or not content.strip():
            flash("File appears to be empty or unreadable", "error")
            return redirect(url_for('index'))
        
        # Get or create knowledge base
        kb_name = config.get('kb_name', 'texttrove_kb')
        try:
            kb = server.knowledge_bases.get(kb_name)
        except:
            kb = server.knowledge_bases.create(
                name=kb_name,
                model='sentence_transformers'
            )
        
        # Insert document
        category = request.form.get('category', 'general')
        kb.insert([{
            'content': content,
            'metadata': {
                'category': category,
                'date_added': str(datetime.date.today()),
                'source': file.filename,
                'uploaded_via': 'web_interface'
            }
        }])
        
        flash(f"Successfully uploaded and processed: {file.filename}", "success")
        
    except Exception as e:
        flash(f"Upload error: {str(e)}", "error")
    
    return redirect(url_for('index'))

@app.route('/status')
def status():
    """Show system status"""
    status_info = {
        'mindsdb_connected': server is not None,
        'mindsdb_url': config.get('mindsdb_url', 'http://127.0.0.1:47334'),
        'kb_name': config.get('kb_name', 'texttrove_kb'),
        'knowledge_bases': []
    }
    
    if server:
        try:
            kbs = server.knowledge_bases.list()
            status_info['knowledge_bases'] = [kb.name for kb in kbs] if kbs else []
        except:
            status_info['knowledge_bases'] = ['Error loading KBs']
    
    return render_template('status.html', status=status_info)

if __name__ == '__main__':
    if not server:
        print("Warning: MindsDB connection failed. Web app will have limited functionality.")
    
    print("Starting TextSpark Web App...")
    print("Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)