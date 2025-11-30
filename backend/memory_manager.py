from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_, or_, func
from shared.models import Memory, Setting
import os
import json
from typing import List, Dict, Any, Optional

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://luma:lumapass@db:5432/luma')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class MemoryManager:
    """Class to handle memory operations"""
    
    @staticmethod
    def get_memories(user_id: Optional[str] = None, approved: Optional[bool] = True, 
                     source: Optional[str] = None, limit: Optional[int] = None) -> List[Memory]:
        """Get memories with optional filters"""
        session = Session()
        try:
            query = session.query(Memory)
            
            if user_id:
                query = query.filter(Memory.user_id == user_id)
            if approved is not None:
                query = query.filter(Memory.approved == approved)
            if source:
                query = query.filter(Memory.source == source)
                
            query = query.order_by(Memory.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
                
            return query.all()
        finally:
            session.close()
    
    @staticmethod
    def search_memories(query_text: str, user_id: Optional[str] = None, 
                        approved: bool = True, limit: int = 10) -> List[Memory]:
        """Search memories by content with optional filters"""
        session = Session()
        try:
            query = session.query(Memory)
            
            # Search in content field
            query = query.filter(Memory.content.ilike(f'%{query_text}%'))
            
            if user_id:
                query = query.filter(Memory.user_id == user_id)
            if approved:
                query = query.filter(Memory.approved == approved)
                
            query = query.order_by(Memory.timestamp.desc())
            
            return query.limit(limit).all()
        finally:
            session.close()
    
    @staticmethod
    def add_memory(user_id: str, content: str, memory_type: str = 'long', 
                   source: str = 'manual', importance: int = 0, 
                   tags: Optional[List[str]] = None, approved: bool = True) -> Memory:
        """Add a new memory"""
        session = Session()
        try:
            new_memory = Memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                source=source,
                importance=importance,
                tags=json.dumps(tags) if tags else None,
                approved=approved
            )
            
            session.add(new_memory)
            session.commit()
            
            return new_memory
        finally:
            session.close()
    
    @staticmethod
    def update_memory(memory_id: int, content: Optional[str] = None,
                      memory_type: Optional[str] = None, importance: Optional[int] = None,
                      tags: Optional[List[str]] = None, approved: Optional[bool] = None) -> bool:
        """Update an existing memory"""
        session = Session()
        try:
            memory = session.query(Memory).filter(Memory.id == memory_id).first()
            if not memory:
                return False
                
            if content is not None:
                memory.content = content
            if memory_type is not None:
                memory.memory_type = memory_type
            if importance is not None:
                memory.importance = importance
            if tags is not None:
                memory.tags = json.dumps(tags)
            if approved is not None:
                memory.approved = approved
                
            session.commit()
            return True
        finally:
            session.close()
    
    @staticmethod
    def delete_memory(memory_id: int) -> bool:
        """Delete a memory"""
        session = Session()
        try:
            memory = session.query(Memory).filter(Memory.id == memory_id).first()
            if not memory:
                return False
                
            session.delete(memory)
            session.commit()
            return True
        finally:
            session.close()
    
    @staticmethod
    def approve_memory_suggestion(memory_id: int) -> bool:
        """Approve an AI-suggested memory"""
        session = Session()
        try:
            memory = session.query(Memory).filter(
                and_(Memory.id == memory_id, Memory.source == 'ai_suggested')
            ).first()
            
            if not memory:
                return False
                
            memory.approved = True
            session.commit()
            return True
        finally:
            session.close()
    
    @staticmethod
    def get_relevant_memories(user_id: str, context_limit: int = 5) -> List[Memory]:
        """Get the most relevant memories for a user based on importance and recency"""
        session = Session()
        try:
            # Get approved memories for the user, ordered by importance and timestamp
            memories = session.query(Memory).filter(
                and_(
                    Memory.user_id == user_id,
                    Memory.approved == True
                )
            ).order_by(
                Memory.importance.desc(),
                Memory.timestamp.desc()
            ).limit(context_limit).all()
            
            return memories
        finally:
            session.close()
    
    @staticmethod
    def add_memory_suggestion(user_id: str, content: str, importance: int = 0,
                              tags: Optional[List[str]] = None) -> Memory:
        """Add an AI-suggested memory (not yet approved)"""
        return MemoryManager.add_memory(
            user_id=user_id,
            content=content,
            memory_type='long',  # Suggestions are always long-term
            source='ai_suggested',
            importance=importance,
            tags=tags,
            approved=False
        )