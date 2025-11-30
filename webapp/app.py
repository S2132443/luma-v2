import tempfile
import PyPDF2
import pandas as pd
import json as json_module
from flask import Flask, render_template, request, redirect, jsonify
from shared.models import Base, Setting, Log, TokenUsage, Memory
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
import os
import json
from backend.memory_manager import MemoryManager
from backend.llm_interface import get_current_provider
import openpyxl

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://luma:lumapass@db:5432/luma')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

@app.route('/')
def chat():
    return render_template('chat.html')

# Alias for chat route
@app.route('/chat')
def chat_alias():
    return render_template('chat.html')

def get_setting_value(key, default=None):
    """Helper function to get setting value from database"""
    session = Session()
    try:
        setting = session.query(Setting).filter_by(key=key).first()
        return setting.value if setting else default
    finally:
        session.close()

@app.route('/dashboard')
def dashboard():
    session = Session()
    # Total token usage
    from sqlalchemy import func
    total_usage = session.query(func.sum(TokenUsage.total_tokens)).scalar() or 0
    # Recent logs
    recent_logs = session.query(Log).order_by(Log.timestamp.desc()).limit(10).all()
    session.close()
    return render_template('dashboard.html', total_tokens=total_usage, logs=recent_logs)

@app.route('/logs')
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    session = Session()
    offset = (page - 1) * per_page
    logs_items = session.query(Log).order_by(Log.timestamp.desc()).offset(offset).limit(per_page).all()
    total = session.query(Log).count()
    session.close()
    # Simple pagination info
    has_prev = page > 1
    has_next = offset + per_page < total
    prev_num = page - 1 if has_prev else None
    next_num = page + 1 if has_next else None
    return render_template('logs.html', logs=logs_items, page=page, pages=(total // per_page) + 1, has_prev=has_prev, has_next=has_next, prev_num=prev_num, next_num=next_num)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    session = Session()
    success = False
    if request.method == 'POST':
        deepseek_key = request.form.get('deepseek_api_key')
        discord_token = request.form.get('discord_token')
        personality = request.form.get('personality')
        model_provider = request.form.get('model_provider', 'deepseek')
        ollama_endpoint = request.form.get('ollama_endpoint')
        ollama_model = request.form.get('ollama_model')

        # Update DeepSeek API key
        if deepseek_key is not None:  # Allow empty string to clear the key
            setting = session.query(Setting).filter_by(key='deepseek_api_key').first()
            if setting:
                setting.value = deepseek_key
            else:
                setting = Setting(key='deepseek_api_key', value=deepseek_key)
                session.add(setting)

        # Update Discord token
        if discord_token is not None:
            setting = session.query(Setting).filter_by(key='discord_token').first()
            if setting:
                setting.value = discord_token
            else:
                setting = Setting(key='discord_token', value=discord_token)
                session.add(setting)

        # Update personality
        if personality is not None:
            setting = session.query(Setting).filter_by(key='personality').first()
            if setting:
                setting.value = personality
            else:
                setting = Setting(key='personality', value=personality)
                session.add(setting)

        # Update model provider
        setting = session.query(Setting).filter_by(key='model_provider').first()
        if setting:
            setting.value = model_provider
        else:
            setting = Setting(key='model_provider', value=model_provider)
            session.add(setting)

        # Update Ollama endpoint
        if ollama_endpoint is not None:
            setting = session.query(Setting).filter_by(key='ollama_endpoint').first()
            if setting:
                setting.value = ollama_endpoint
            else:
                setting = Setting(key='ollama_endpoint', value=ollama_endpoint)
                session.add(setting)

        # Update Ollama model
        if ollama_model is not None:
            setting = session.query(Setting).filter_by(key='ollama_model').first()
            if setting:
                setting.value = ollama_model
            else:
                setting = Setting(key='ollama_model', value=ollama_model)
                session.add(setting)

        # Update memory suggestions enabled setting
        memory_suggestions_enabled = request.form.get('memory_suggestions_enabled', 'false')
        setting = session.query(Setting).filter_by(key='memory_suggestions_enabled').first()
        if setting:
            setting.value = memory_suggestions_enabled
        else:
            setting = Setting(key='memory_suggestions_enabled', value=memory_suggestions_enabled)
            session.add(setting)

        session.commit()
        success = True

    # Get all settings
    deepseek_key = session.query(Setting).filter_by(key='deepseek_api_key').first()
    discord_token = session.query(Setting).filter_by(key='discord_token').first()
    personality = session.query(Setting).filter_by(key='personality').first()
    model_provider = session.query(Setting).filter_by(key='model_provider').first()
    ollama_endpoint = session.query(Setting).filter_by(key='ollama_endpoint').first()
    ollama_model = session.query(Setting).filter_by(key='ollama_model').first()
    memory_suggestions_setting = session.query(Setting).filter_by(key='memory_suggestions_enabled').first()

    session.close()

    return render_template('settings.html',
                           deepseek_key=deepseek_key.value if deepseek_key else '',
                           discord_token=discord_token.value if discord_token else '',
                           personality=personality.value if personality else 'You are a helpful AI assistant.',
                           model_provider=model_provider.value if model_provider else 'deepseek',
                           ollama_endpoint=ollama_endpoint.value if ollama_endpoint else 'http://localhost:11434',
                           ollama_model=ollama_model.value if ollama_model else 'llama2',
                           memory_suggestions_enabled=memory_suggestions_setting.value if memory_suggestions_setting else 'false',
                           success=success)

@app.route('/memory', methods=['GET', 'POST'])
def memory():
    session = Session()
    success = False
    error = None
    memory_suggestions = []

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        memory_type = request.form.get('memory_type')
        content = request.form.get('content')
        source = request.form.get('source', 'manual')  # Default to manual
        importance = request.form.get('importance', 0, type=int)
        tags_str = request.form.get('tags', '')

        # Parse tags from comma-separated string
        tags = [tag.strip() for tag in tags_str.split(',')] if tags_str else []

        if user_id and content:  # memory_type is optional now
            try:
                new_memory = MemoryManager.add_memory(
                    user_id=user_id,
                    content=content,
                    memory_type=memory_type or 'long',  # Default to 'long'
                    source=source,
                    importance=importance,
                    tags=tags,
                    approved=True  # Manual entries are approved by default
                )
                success = True
            except Exception as e:
                error = f"Error adding memory: {str(e)}"
        else:
            error = "User ID and content are required"

    # Get regular memories (approved)
    memories = MemoryManager.get_memories(approved=True)

    # Get pending memory suggestions
    memory_suggestions = MemoryManager.get_memories(source='ai_suggested', approved=False)

    session.close()
    return render_template('memory.html', memories=memories, memory_suggestions=memory_suggestions, success=success, error=error)

@app.route('/memory/delete/<int:memory_id>', methods=['POST'])
def delete_memory(memory_id):
    success = MemoryManager.delete_memory(memory_id)
    return redirect('/memory')

@app.route('/memory/approve/<int:memory_id>', methods=['POST'])
def approve_memory(memory_id):
    success = MemoryManager.approve_memory_suggestion(memory_id)
    return redirect('/memory')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '')
    user_id = data.get('user_id', 'web_user')  # Default user ID for web chat
    include_memory_suggestions = data.get('include_memory_suggestions', False)  # Default to False

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    try:
        # Get the current LLM provider based on settings
        llm_provider = get_current_provider()

        # Fetch personality from database
        session = Session()
        personality_setting = session.query(Setting).filter_by(key='personality').first()
        personality = personality_setting.value if personality_setting else 'You are a helpful AI assistant.'

        # Check if memory suggestions are enabled
        memory_suggestions_enabled_setting = session.query(Setting).filter_by(key='memory_suggestions_enabled').first()
        memory_suggestions_enabled = (memory_suggestions_enabled_setting.value == 'true') if memory_suggestions_enabled_setting else False

        # Override with request parameter if provided, but respect global setting as default
        if 'include_memory_suggestions' in data:
            include_memory_suggestions = data['include_memory_suggestions']
        else:
            include_memory_suggestions = memory_suggestions_enabled

        session.close()

        # Get relevant memories for the user
        long_term_memory = get_long_memory(user_id)

        # Build prompt with personality and memory context
        system_prompt = f"{personality}\n\nLong-term memory:\n{long_term_memory if long_term_memory else 'No previous memories.'}\n\nConversation history:"

        messages = [{'role': 'system', 'content': system_prompt}]
        messages.append({'role': 'user', 'content': user_message})

        # Get response from LLM
        response_data = llm_provider.chat_completion(
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )

        bot_response = response_data['content']
        input_tokens = response_data['input_tokens']
        output_tokens = response_data['output_tokens']

        # Generate memory suggestions only if enabled
        if include_memory_suggestions:
            memory_suggestions = llm_provider.extract_memory_suggestions(user_message, bot_response)

            # Add memory suggestions to the database as unapproved memories
            for suggestion in memory_suggestions:
                MemoryManager.add_memory_suggestion(
                    user_id=user_id,
                    content=suggestion,
                    importance=1,  # Default low importance for suggestions
                    tags=['suggested', 'web-chat']
                )

        # Log the interaction
        log_interaction(
            user_id=user_id,
            username='web_user',  # Default username for web interactions
            channel_id='web_chat',  # Default channel for web interactions
            user_msg=user_message,
            bot_resp=bot_response,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        return jsonify({
            'response': bot_response,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': response_data['total_tokens'],
            'memory_suggestions_enabled': include_memory_suggestions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload_document', methods=['POST'])
def upload_document_api():
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No document provided'}), 400

    file = request.files['document']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No document selected'}), 400

    user_id = request.form.get('user_id', 'web_user')

    try:
        # Create a temporary file to process the uploaded document
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_filename = temp_file.name

        # Process the document based on its extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        content = ""

        if file_extension == '.txt':
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
        elif file_extension == '.pdf':
            with open(temp_filename, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(temp_filename)
            content = df.to_string()
        elif file_extension == '.json':
            with open(temp_filename, 'r', encoding='utf-8') as f:
                json_data = json_module.load(f)
                content = json_module.dumps(json_data, indent=2)
        elif file_extension == '.csv':
            df = pd.read_csv(temp_filename)
            content = df.to_string()
        else:
            # For any other text-based formats
            try:
                with open(temp_filename, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # If it's not a text file, let the user know
                os.unlink(temp_filename)
                return jsonify({'success': False, 'error': f'Unsupported file type: {file_extension}'}), 400

        # Clean up the temporary file
        os.unlink(temp_filename)

        # Add the document content to memories
        # We'll break large content into chunks to avoid overly long memories
        max_chunk_size = 2000
        chunks = [content[i:i+max_chunk_size] for i in range(0, len(content), max_chunk_size)]

        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Only add non-empty chunks
                memory_tags = ['document', f'doc-{file_extension[1:]}', f'chunk-{i+1}']

                MemoryManager.add_memory(
                    user_id=user_id,
                    content=chunk,
                    memory_type='long',
                    source='document_upload',
                    importance=0,
                    tags=memory_tags,
                    approved=True
                )

        return jsonify({'success': True, 'message': f'Document processed and added to memories in {len(chunks)} chunks'})

    except Exception as e:
        # Make sure to clean up the temp file in case of error
        if 'temp_filename' in locals():
            try:
                os.unlink(temp_filename)
            except:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/memory/search', methods=['GET'])
def search_memory_api():
    query = request.args.get('q', '')
    user_id = request.args.get('user_id', None)

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        results = MemoryManager.search_memories(query, user_id=user_id)
        memories_data = []
        for memory in results:
            memories_data.append({
                'id': memory.id,
                'user_id': memory.user_id,
                'memory_type': memory.memory_type,
                'content': memory.content,
                'timestamp': memory.timestamp.isoformat() if memory.timestamp else None,
                'source': memory.source,
                'importance': memory.importance,
                'tags': json.loads(memory.tags) if memory.tags else [],
                'approved': memory.approved
            })

        return jsonify({'memories': memories_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_long_memory(user_id):
    """Get relevant long-term memories for a user"""
    memories = MemoryManager.get_relevant_memories(user_id, context_limit=5)
    return '\n'.join([m.content for m in memories])


def log_interaction(user_id, username, channel_id, user_msg, bot_resp, input_tokens, output_tokens):
    """Log the interaction to the database"""
    session = Session()
    log = Log(user_id=user_id, username=username, channel_id=channel_id,
              user_message=user_msg, bot_response=bot_resp,
              input_tokens=input_tokens, output_tokens=output_tokens)
    session.add(log)
    # Update token usage
    usage = TokenUsage(total_tokens=input_tokens + output_tokens,
                       input_tokens=input_tokens, output_tokens=output_tokens)
    session.add(usage)
    session.commit()
    session.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
