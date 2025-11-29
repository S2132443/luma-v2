from flask import Flask, render_template, request, redirect
from shared.models import Base, Setting, Log, TokenUsage, Memory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://luma:lumapass@db:5432/luma')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

@app.route('/')
def landing():
    return render_template('landing.html')

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
        if deepseek_key:
            setting = session.query(Setting).filter_by(key='deepseek_api_key').first()
            if setting:
                setting.value = deepseek_key
            else:
                setting = Setting(key='deepseek_api_key', value=deepseek_key)
                session.add(setting)
        if discord_token:
            setting = session.query(Setting).filter_by(key='discord_token').first()
            if setting:
                setting.value = discord_token
            else:
                setting = Setting(key='discord_token', value=discord_token)
                session.add(setting)
        if personality:
            setting = session.query(Setting).filter_by(key='personality').first()
            if setting:
                setting.value = personality
            else:
                setting = Setting(key='personality', value=personality)
                session.add(setting)
        session.commit()
        success = True
    deepseek_key = session.query(Setting).filter_by(key='deepseek_api_key').first()
    discord_token = session.query(Setting).filter_by(key='discord_token').first()
    personality = session.query(Setting).filter_by(key='personality').first()
    session.close()
    return render_template('settings.html',
                           deepseek_key=deepseek_key.value if deepseek_key else '',
                           discord_token=discord_token.value if discord_token else '',
                           personality=personality.value if personality else 'You are a helpful AI assistant.',
                           success=success)

@app.route('/memory', methods=['GET', 'POST'])
def memory():
    session = Session()
    success = False
    error = None

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        memory_type = request.form.get('memory_type')
        content = request.form.get('content')

        if user_id and memory_type and content:
            new_memory = Memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content
            )
            session.add(new_memory)
            session.commit()
            success = True
        else:
            error = "All fields are required"

    memories = session.query(Memory).order_by(Memory.timestamp.desc()).all()
    session.close()
    return render_template('memory.html', memories=memories, success=success, error=error)

@app.route('/memory/delete/<int:memory_id>', methods=['POST'])
def delete_memory(memory_id):
    session = Session()
    memory_item = session.query(Memory).filter_by(id=memory_id).first()
    if memory_item:
        session.delete(memory_item)
        session.commit()
    session.close()
    return redirect('/memory')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
