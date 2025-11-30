from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)  # Encrypted for keys

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), nullable=False)
    username = Column(String(100), nullable=False)
    channel_id = Column(String(20), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)

class TokenUsage(Base):
    __tablename__ = 'token_usages'
    id = Column(Integer, primary_key=True)
    total_tokens = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = 'memories'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), nullable=False)
    memory_type = Column(String(10), nullable=False)  # 'short' or 'long'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(20), default='manual')  # 'manual' or 'ai_suggested'
    importance = Column(Integer, default=0)  # Score for memory relevance
    tags = Column(Text)  # JSON array for memory categorization
    approved = Column(Boolean, default=True)  # For AI-suggested memories