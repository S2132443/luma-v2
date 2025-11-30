import discord
from discord import app_commands
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from collections import deque
from datetime import datetime
from shared.models import Base, Setting, Log, TokenUsage, Memory
from backend.llm_interface import create_llm_provider, get_current_provider
from backend.memory_manager import MemoryManager

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
    """Get relevant long-term memories for a user"""
    memories = MemoryManager.get_relevant_memories(user_id, context_limit=5)
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

    try:
        # Get the current LLM provider based on settings
        llm_provider = get_current_provider()

        # Fetch personality from database on each request - updates are applied immediately
        personality = get_setting('personality') or 'You are a helpful AI assistant.'

        # Build prompt with long-term memory
        long_term_memory = get_long_memory(user_id)
        system_prompt = f"{personality}\n\nLong-term memory:\n{long_term_memory if long_term_memory else 'No previous memories.'}\n\nConversation history:"

        messages = [{'role': 'system', 'content': system_prompt}]

        # Add short-term memory if available
        if user_id in short_memory:
            messages.extend(list(short_memory[user_id]))

        messages.append({'role': 'user', 'content': message})

        # Get response from LLM
        response_data = llm_provider.chat_completion(
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )

        bot_response = response_data['content']
        input_tokens = response_data['input_tokens']
        output_tokens = response_data['output_tokens']

        # Generate memory suggestions
        memory_suggestions = llm_provider.extract_memory_suggestions(message, bot_response)

        # Add memory suggestions to the database as unapproved memories
        for suggestion in memory_suggestions:
            MemoryManager.add_memory_suggestion(
                user_id=user_id,
                content=suggestion,
                importance=1,  # Default low importance for suggestions
                tags=['suggested']
            )

        # Update short-term memory
        update_short_memory(user_id, 'user', message)
        update_short_memory(user_id, 'assistant', bot_response)

        # Log the interaction
        log_interaction(user_id, username, channel_id, message, bot_response, input_tokens, output_tokens)

        await interaction.followup.send(bot_response)

    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")
        print(f"Error in chat command: {str(e)}")

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
