import discord
from discord import app_commands
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from collections import deque
from datetime import datetime
from shared.models import Base, Setting, Log, TokenUsage, Memory

# DB setup
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://luma:lumapass@db:5432/luma')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Short-term memory: {user_id: deque([{'role': 'user', 'content': msg}, ...], maxlen=10)}
short_memory = {}

def get_setting(key):
    session = Session()
    setting = session.query(Setting).filter_by(key=key).first()
    session.close()
    return setting.value if setting else None

def set_setting(key, value):
    session = Session()
    setting = session.query(Setting).filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        session.add(setting)
    session.commit()
    session.close()

def get_long_memory(user_id):
    session = Session()
    memories = session.query(Memory).filter_by(user_id=user_id, memory_type='long').all()
    session.close()
    return '\n'.join([m.content for m in memories])

def update_short_memory(user_id, role, content):
    if user_id not in short_memory:
        short_memory[user_id] = deque(maxlen=10)
    short_memory[user_id].append({'role': role, 'content': content})

def log_interaction(user_id, username, channel_id, user_msg, bot_resp, input_tokens, output_tokens):
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

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name="chat", description="Chat with the AI bot")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    username = interaction.user.name
    channel_id = str(interaction.channel.id)

    # Fetch personality from database on each request - updates are applied immediately
    personality = get_setting('personality') or 'You are a helpful AI assistant.'
    deepseek_key = get_setting('deepseek_api_key')
    if not deepseek_key:
        await interaction.followup.send("API key not set. Please configure in dashboard.")
        return

    # Build prompt
    system_prompt = f"{personality}\n\nLong-term memory:\n{get_long_memory(user_id)}\n\nConversation history:"
    messages = [{'role': 'system', 'content': system_prompt}]
    if user_id in short_memory:
        messages.extend(list(short_memory[user_id]))
    messages.append({'role': 'user', 'content': message})

    openai_client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com/v1")
    try:
        response = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=150
        )
        bot_response = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")
        return

    # Update memories
    update_short_memory(user_id, 'user', message)
    update_short_memory(user_id, 'assistant', bot_response)

    # Log
    log_interaction(user_id, username, channel_id, message, bot_response, input_tokens, output_tokens)

    await interaction.followup.send(bot_response)

@client.event
async def on_ready():
    await tree.sync()
    print(f'Bot logged in as {client.user}')

if __name__ == "__main__":
    discord_token = get_setting('discord_token')
    if not discord_token:
        print("Discord token not set.")
        exit(1)
    client.run(discord_token)
