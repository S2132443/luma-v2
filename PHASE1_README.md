# Luma-v2: Multimodal AI VTuber / Streamer / Discord Bot

## Overview
Luma-v2 is a Discord AI bot with web-based management, now enhanced with advanced memory capabilities and multi-model support. This multimodal AI system allows for text chat with hybrid memory management, supporting both DeepSeek API and local Ollama models.

## Phase 1: Text Chat + Hybrid Memory Features

### Core Features
- **Enhanced Memory System**: Track and manage user-specific memories with importance ratings and tags
- **AI-Generated Memory Suggestions**: The AI automatically suggests important information to remember
- **Multi-Model Support**: Choose between DeepSeek API or local Ollama models
- **Web Dashboard**: Comprehensive interface for managing memories, settings, and logs
- **Discord Integration**: Slash command interface for seamless chat experience

### Memory System
- **Manual Memories**: Add, edit, and delete memories directly through the web interface
- **AI-Suggested Memories**: The system automatically suggests important information during conversations
- **Importance Ratings**: Rate memories from 0-10 to control context inclusion
- **Tagging System**: Organize memories with comma-separated tags
- **Memory Approval**: Review and approve AI-suggested memories before they become active
- **Search Functionality**: Find memories by content with the `/api/memory/search` endpoint

### Model Selection
- **DeepSeek API**: High-quality responses via API (default)
- **Ollama (Local)**: Privacy-focused local models without data leaving your system
- **Easy Switching**: Toggle between providers in the settings interface

## Installation & Setup

### Prerequisites
- Docker and Docker Compose
- DeepSeek API key (for API mode) or Ollama (for local models)

### Quick Start
1. Clone the repository
2. Set up your environment:
   ```bash
   # For DeepSeek mode
   # Add your DeepSeek API key in the web dashboard
   
   # For Ollama mode
   # Make sure Ollama is running and has a model installed (e.g., llama2)
   ```

3. Build and start the services:
   ```bash
   docker-compose up -d --build
   ```

4. Access the web dashboard at `http://localhost:5000`
5. Configure your bot settings and add your Discord token
6. Invite the bot to your server using Discord developer portal

## API Endpoints

### Memory Endpoints
- `GET /api/memory/search?q=query&user_id=optional_user_id` - Search memories by content
- `POST /memory` - Add new memory
- `POST /memory/delete/<id>` - Delete memory
- `POST /memory/approve/<id>` - Approve AI-suggested memory

### Settings Endpoints
- `GET /settings` - View and update bot settings
- `POST /settings` - Save bot settings

## Configuration

### Model Provider Settings
The system supports two model providers:

#### DeepSeek API (Default)
- API Key: Enter your DeepSeek API key in the settings page
- Model: deepseek-chat
- No local resources required

#### Ollama (Local Models)
- Endpoint: Default `http://ollama:11434` (when using docker-compose)
- Model: Default `llama2`
- Requires local Ollama service with a model installed

### Memory Settings
- Context Limit: Maximum memories to include in AI conversations
- Memory Types: 'short' (ephemeral) or 'long' (persistent)
- Source: 'manual' (user-added) or 'ai_suggested' (AI-generated)
- Approval: Manual entries auto-approved, AI suggestions require approval

## Architecture
- **PostgreSQL Database**: Central storage for memories, logs, and settings
- **Discord Bot**: Handles slash commands and chat interactions
- **Web Dashboard**: Flask-based interface for management
- **LLM Interface**: Pluggable system supporting multiple model providers
- **Memory Manager**: Centralized memory operations with search and retrieval

## Memory Suggestion Workflow
1. User sends message to Discord bot
2. Bot processes with selected LLM provider
3. LLM analyzes conversation to identify important information
4. Suggested memories stored as unapproved entries
5. Admin reviews suggestions in web dashboard
6. Approved memories become available for future context

## Docker Services
- `db`: PostgreSQL database for persistent storage
- `bot`: Discord bot service with AI integration
- `webapp`: Web dashboard for management
- `ollama`: (Optional) Local model service for privacy-focused usage

## Extending to Future Phases
This Phase 1 implementation provides a solid foundation for:
- Phase 2: Voice input/output integration
- Phase 3: Avatar display and reactions
- Phase 4: Vision processing capabilities
- Phase 5: Advanced memory LLM
- Phase 6: OBS and Twitch integration
- Phase 7: Enhanced Discord capabilities

## Troubleshooting
- If the bot doesn't respond, check that the Discord token is correctly set in settings
- For API connection issues, verify your model provider settings
- For memory suggestions not appearing, ensure the LLM has sufficient context to identify important information