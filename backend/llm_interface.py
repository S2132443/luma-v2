from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from shared.models import Memory, Setting
from openai import OpenAI
import requests
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://luma:lumapass@db:5432/luma')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class LLMInterface(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], 
                       max_tokens: int = 150, 
                       temperature: float = 0.7) -> Dict[str, Any]:
        """Generate chat completion"""
        pass

    @abstractmethod
    def extract_memory_suggestions(self, user_message: str, bot_response: str) -> List[str]:
        """Extract memory suggestions from conversation"""
        pass


class DeepSeekInterface(LLMInterface):
    """DeepSeek API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       max_tokens: int = 150, 
                       temperature: float = 0.7) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                'content': response.choices[0].message.content,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.prompt_tokens + response.usage.completion_tokens
            }
        except Exception as e:
            raise Exception(f"DeepSeek API error: {str(e)}")
    
    def extract_memory_suggestions(self, user_message: str, bot_response: str) -> List[str]:
        """
        Extract memory suggestions using the LLM by asking it to identify important
        information that should be remembered.
        """
        prompt = f"""
        Analyze the following conversation and suggest important memories that should be retained:
        
        User: {user_message}
        AI: {bot_response}
        
        Respond with a JSON array of memory suggestions. Each suggestion should be a concise statement about something important that should be remembered. Only return the JSON array with no other text.
        """
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            
            # Extract JSON from response
            content = response.choices[0].message.content.strip()
            # Remove any markdown formatting
            if content.startswith('```json'):
                content = content[7:content.rfind('```')]
            elif content.startswith('```'):
                content = content[3:content.rfind('```')]
            
            suggestions = json.loads(content)
            if isinstance(suggestions, list):
                return suggestions
            else:
                return []
        except Exception as e:
            print(f"Error extracting memory suggestions: {e}")
            return []


class OllamaInterface(LLMInterface):
    """Ollama API implementation"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       max_tokens: int = 150, 
                       temperature: float = 0.7) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate tokens - Ollama doesn't always provide exact token counts
            # We'll estimate based on character count as a fallback
            input_tokens = len(" ".join([msg.get("content", "") for msg in messages]))
            output_tokens = len(data.get('message', {}).get('content', ''))
            
            return {
                'content': data['message']['content'],
                'input_tokens': data.get('eval_count', input_tokens // 4),  # Rough estimation
                'output_tokens': data.get('prompt_eval_count', output_tokens // 4),  # Rough estimation
                'total_tokens': data.get('eval_count', input_tokens // 4) + data.get('prompt_eval_count', output_tokens // 4)
            }
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def extract_memory_suggestions(self, user_message: str, bot_response: str) -> List[str]:
        """
        Extract memory suggestions using the local Ollama model.
        """
        prompt = f"""
        Analyze the following conversation and suggest important memories that should be retained:
        
        User: {user_message}
        AI: {bot_response}
        
        Respond with a JSON array of memory suggestions. Each suggestion should be a concise statement about something important that should be remembered. Only return the JSON array with no other text.
        """
        
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "options": {
                "temperature": 0.3,
                "num_predict": 200
            },
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            content = data['message']['content'].strip()
            
            # Remove any markdown formatting
            if content.startswith('```json'):
                content = content[7:content.rfind('```')]
            elif content.startswith('```'):
                content = content[3:content.rfind('```')]
            
            suggestions = json.loads(content)
            if isinstance(suggestions, list):
                return suggestions
            else:
                return []
        except Exception as e:
            print(f"Error extracting memory suggestions from Ollama: {e}")
            return []


def create_llm_provider(provider_type: str, **kwargs) -> LLMInterface:
    """Factory function to create the appropriate LLM provider"""
    if provider_type.lower() == 'deepseek':
        api_key = kwargs.get('api_key')
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        return DeepSeekInterface(api_key)
    elif provider_type.lower() == 'ollama':
        base_url = kwargs.get('base_url', 'http://localhost:11434')
        model = kwargs.get('model', 'llama2')
        return OllamaInterface(base_url, model)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")


def get_current_provider() -> LLMInterface:
    """Get the currently configured LLM provider based on settings"""
    session = Session()
    try:
        # Get provider type
        provider_setting = session.query(Setting).filter_by(key='model_provider').first()
        provider_type = provider_setting.value if provider_setting else 'deepseek'

        if provider_type == 'deepseek':
            api_key_setting = session.query(Setting).filter_by(key='deepseek_api_key').first()
            if not api_key_setting:
                raise ValueError("DeepSeek API key not configured")
            return create_llm_provider('deepseek', api_key=api_key_setting.value)
        elif provider_type == 'ollama':
            endpoint_setting = session.query(Setting).filter_by(key='ollama_endpoint').first()
            model_setting = session.query(Setting).filter_by(key='ollama_model').first()

            base_url = endpoint_setting.value if endpoint_setting else 'http://localhost:11434'
            model = model_setting.value if model_setting else 'llama2'

            return create_llm_provider('ollama', base_url=base_url, model=model)
        else:
            # Default to DeepSeek if no provider is set
            api_key_setting = session.query(Setting).filter_by(key='deepseek_api_key').first()
            if api_key_setting:
                return create_llm_provider('deepseek', api_key=api_key_setting.value)
            else:
                raise ValueError("No LLM provider configured")
    finally:
        session.close()