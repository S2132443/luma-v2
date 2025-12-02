
# Multimodal AI VTuber / Streamer / Discord Bot Development Plan

---

## Overview
This project aims to build a modular, Dockerized web application that allows:

- AI VTuber / streamer with avatar (PNG / Live2D / 3D)  
- Multimodal inputs: text, voice, vision, Twitch chat  
- Realtime outputs: text, TTS, avatar reactions  
- Memory management: hybrid (manual + AI suggestions) or optional Memory LLM  
- OBS integration for streaming  
- Discord bot for multi-speaker voice and text channels  

All modules are **toggleable**, allowing you to enable only the features you need.

---

## Tech Stack

### Backend
- **Language / Framework:** Python / FastAPI  
- **Realtime:** WebSockets / WebRTC for audio/video  
- **Task Queue (Phase 1 Enhancement):** Celery with Redis/RabbitMQ for async tasks  
- **Database / Memory:**  
  - Short-term memory: in-memory dict / Redis  
  - Long-term memory: Vector DB (ChromaDB, Weaviate) + SQLite fallback

### Asynchronous Task Processing (Celery Integration)
**Phase 1 Enhancement: Background Task Management**

To improve scalability and responsiveness, Phase 1 will integrate Celery for handling computationally intensive and I/O-bound operations asynchronously:

#### **Celery Workers for Phase 1 Tasks**
- **Memory Processing Worker**: Handles memory suggestion generation, extraction, and database operations
- **Document Processing Worker**: Processes uploaded documents (PDF, Excel, TXT, JSON, CSV) in the background
- **LLM API Worker**: Manages API calls to external LLM providers with retry logic and rate limiting
- **Token Usage Worker**: Tracks and aggregates token usage metrics across all operations

#### **Task Queue Architecture**
\`\`\`
User Request → FastAPI Backend → Celery Task Queue
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │        Celery Workers           │
                    ├─────────────────────────────────┤
                    │ • Memory Processing             │
                    │ • Document Processing           │
                    │ • LLM API Calls                 │
                    │ • Token Tracking                │
                    └─────────────────────────────────┘
                                    │
                                    ▼
                              Redis/RabbitMQ
                              (Message Broker)
\`\`\`

#### **Benefits of Celery Integration**
- **Improved Responsiveness**: Web requests don't block on heavy computations
- **Scalability**: Workers can be scaled independently based on load
- **Reliability**: Failed tasks can be retried automatically
- **Resource Management**: CPU-intensive tasks don't impact web server performance
- **Queue Management**: Prioritize critical tasks and handle backpressure

#### **Phase 1 Celery Tasks**
1. **Memory Suggestion Processing**
   - Extract memory suggestions from LLM responses
   - Validate and store suggested memories in database
   - Update memory importance scores and tags

2. **Document Upload Processing**
   - Parse uploaded documents (PDF, Excel, TXT, JSON, CSV)
   - Extract and chunk content for memory storage
   - Process large documents without blocking web requests

3. **LLM API Call Management**
   - Handle API rate limiting and retries
   - Manage API key rotation and fallback providers
   - Track API usage and costs

4. **Token Usage Aggregation**
   - Collect token usage metrics from all operations
   - Generate usage reports and alerts
   - Update database with aggregated statistics

#### **Celery Configuration**
- **Broker**: Redis (already used for caching) or RabbitMQ for production
- **Result Backend**: Redis for task result storage
- **Task Serialization**: JSON for compatibility and debugging
- **Retry Policy**: Exponential backoff for failed API calls
- **Task Timeouts**: Configurable timeouts per task type
- **Worker Concurrency**: Adjustable based on available CPU cores

#### **Docker Integration**
\`\`\`
celery-worker:
  build: ./backend
  command: celery -A backend.celery_app worker --loglevel=info
  depends_on:
    - redis
    - db
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - DATABASE_URL=postgresql://luma:lumapass@db:5432/luma

celery-beat:
  build: ./backend
  command: celery -A backend.celery_app beat --loglevel=info
  depends_on:
    - redis
    - db
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - DATABASE_URL=postgresql://luma:lumapass@db:5432/luma
\`\`\`

### Frontend
- **Framework:** React / Solid / Vue  
- **Components:**  
  - Chat window (text + TTS messages)  
  - Feature toggles: See / Hear / Speak / Memory / Twitch  
  - Webcam / screen share feed  
  - Avatar display (PNG / Live2D / 3D)  
  - Audio playback / microphone capture  

### AI Models - Configurable Providers

Each AI component supports configurable model providers with local and API options:

| Component | Local Options | API Options | Free Options (OpenRouter) |
|-----------|---------------|-------------|---------------------------|
| **Main Thinking LLM** | DeepSeek V3, Qwen 7B, Llama 3 | OpenAI GPT-4o, Claude 3 | GPT-3.5-turbo, Claude Haiku, Llama 3 |
| **Memory Manager LLM** | Phi-3 Mini, Qwen 1.8B | GPT-3.5 Mini, Claude Haiku | GPT-3.5-turbo, Llama 3 |
| **Vision LLM** | Qwen-VL 7B, MiniGPT-4 | GPT-4o Vision API, Claude Vision | LLaVA, Gemini Flash |
| **Voice Model (TTS)** | Kokoro, DIA 1.6B | ElevenLabs, Google TTS | Coqui TTS, Edge TTS |
| **ASR (Speech-to-Text)** | Whisper.cpp, Faster-whisper | OpenAI Whisper API, Deepgram | Vosk, AssemblyAI Free Tier |
| **Internet LLM** | Llama 3, Mixtral | Perplexity API, Phind | OpenRouter Free Models |

### API Provider Management
- **OpenRouter Integration**: Unified API for accessing multiple providers with free tier options
- **Rate Limit Monitoring**: Automatic tracking of API usage across all providers
- **Cost Optimization**: Smart fallback to cheaper/free models when limits are approached
- **Provider Health Checks**: Monitor API availability and response times

### API Limit Warnings & Service Management
- **Smart Shutdown**: Services automatically disable when approaching API limits
- **"Luma Getting Sleepy"**: Friendly notifications when Main Memory LLM limits are reached
- **"Luma Asleep"**: Clear indication when services are disabled due to exhausted limits
- **Limit Recovery**: Automatic service re-enabling when limits reset

### Other Components
- **Avatar Rendering:** PNG / Live2D / 3D via Pixi.js / Three.js / Babylon.js  
- **OBS Integration:** Browser source → frontend  
- **Twitch Chat Integration:** Twitch IRC / WebSocket API  
- **Discord Bot:** discord.py for voice + text channels  

---

## Feature Toggles
\`\`\`json
{
  "think": true,      // Always on
  "hear": true,       // ASR input
  "speak": true,      // TTS output
  "see": true,        // Vision / screen share
  "memory": true,     // Knowledge base / manual memory
  "memory_llm": true, // Optional Memory LLM
  "avatar": true,     // PNG / Live2D / 3D
  "twitch": true      // Twitch chat integration
}
\`\`\`

---

## Phased Development Plan

### Phase 1: Text Chat + Hybrid Memory
**Goals:**
- Chat interface for text conversation  
- Memory system:
  - Manual memory management (add / delete / edit)  
  - Main LLM can suggest important memory entries  

**Components:**
- backend + main-llm + memory-db  
- Frontend: Chat window + Memory panel  

**Flow:**
\`\`\`
User Text → Main LLM → 
          ├─ Text Response → Frontend
          └─ Memory Suggestion → Memory DB
                        ▲
                        │
           User manual add/delete/update
\`\`\`

---

### Phase 2: Voice Input & Output
**Goals:**
- ASR for user speech → text  
- TTS for AI responses → audio output  

**Components:**
- ASR container  
- TTS container  
- Backend routes audio  

**Flow:**
\`\`\`
User Voice → ASR → Text → Main LLM → TTS → Audio Output
\`\`\`

---

### Phase 3: Avatar Integration
**Goals:**
- Display avatar: PNG / Live2D / 3D  
- Avatar reacts to TTS (lip-sync, expressions)  

**Flow:**
\`\`\`
Main LLM → TTS → Phonemes / Emotion → Avatar Update → Frontend Display
\`\`\`

---

### Phase 4: Vision Integration
**Goals:**
- Webcam / screen share input  
- Vision LLM analyzes input → generates context  
- Context passed to Main LLM  

**Flow:**
\`\`\`
Webcam / Screen → Vision LLM → Visual Context → Main LLM → Response
\`\`\`

---

### Phase 5: Optional Memory LLM
**Goals:**
- Monitors all inputs/outputs (text, voice, vision, Twitch chat)  
- Summarizes and updates knowledge base  

**Flow:**
\`\`\`
Main LLM Outputs + Vision Context + ASR Text + Twitch Chat → Memory LLM → Knowledge Base
\`\`\`

---

### Phase 6: Internet LLM Integration
**Goals:**
- Enable AI to search the internet for current information
- Web browsing and information retrieval capabilities
- Separate internet-connected LLM for research tasks
- Integration with OpenRouter for free/low-cost web-connected models

**Components:**
- Internet LLM container
- Web search API integration
- Research task management
- Content filtering and summarization

**Flow:**
\`\`\`
Research Request → Internet LLM → Web Search → Information Retrieval → Summarization → Main LLM → Response
\`\`\`

---

### Phase 7: API Limit Monitoring & Token Management
**Goals:**
- Real-time monitoring of API token usage across all providers
- Automatic service shutdown when approaching limits
- Friendly notifications ("Luma getting sleepy/asleep")
- Cost optimization and budget management
- Multi-service monitoring dashboard

**Components:**
- Token usage tracking service
- API limit monitoring system
- Service health dashboard
- Notification system
- Automatic fallback management

**Flow:**
\`\`\`
API Usage → Token Tracker → Limit Monitor → 
          ├─ Warning Notifications → Dashboard
          ├─ Service Shutdown → Graceful Degradation
          └─ Cost Optimization → Provider Switching
\`\`\`

---

### Phase 8: Advanced Monitoring Dashboard
**Goals:**
- GPU usage monitoring for Ollama users
- System performance metrics
- Combined with Phase 7's token monitoring
- Hardware resource tracking
- Performance optimization insights

**Components:**
- GPU monitoring service
- System metrics collection
- Performance dashboard
- Resource utilization tracking
- Hardware health monitoring

**Flow:**
\`\`\`
System Metrics → Monitoring Service → Dashboard → 
          ├─ GPU Usage → Performance Insights
          ├─ Memory Usage → Optimization Suggestions
          └─ CPU Usage → Resource Management
\`\`\`

---

### Phase 9: OBS + Twitch Chat Integration
**Goals:**
- AI reacts to:
  1. Your voice  
  2. Screen/gameplay  
  3. Twitch chat messages  
- Optional Memory LLM tracks viewers, preferences, recurring topics  

**Components:**
- OBS Browser Source → Frontend  
- Twitch chat listener → Backend → Main LLM  
- TTS → Audio → OBS  
- Avatar → visual reactions  

**Flow:**
\`\`\`
Your Voice → ASR → Main LLM → TTS → OBS Audio
Screen / Game → Vision LLM → Main LLM → Response
Twitch Chat → Backend → Main LLM → Response / Memory
Avatar → reacts to TTS + emotion
\`\`\`

---

### Phase 10: Discord Bot
**Goals:**
- Real-time multi-speaker voice + text channels  
- AI responds to voice and text  
- Optional Memory LLM for context tracking  

**Flow:**
\`\`\`
Discord Voice → ASR → Main LLM → TTS → Discord Voice
Discord Text → Main LLM → Memory LLM → Text Reply
\`\`\`

---

## Dockerized Architecture

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                    Frontend                             │
│ Chat + Avatar + Webcam + OBS + Dashboard + Monitoring   │
└─────────────┬──────────────────────┬────────────────────┘
              │ WebSocket / WebRTC   │ System Metrics
              ▼                      ▼
┌─────────────────────────────┐ ┌─────────────────────────┐
│          Backend            │ │   Monitoring Service    │
│ FastAPI / Feature Flags     │ │ Token Usage + GPU Stats │
└─────┬───────┬───────────────┘ └─────────────┬───────────┘
      │       │                               │
      ▼       ▼                               ▼
Main LLM   Vision LLM (optional)    API Limit Monitor
      │                               │
      ▼                               ▼
Optional Memory LLM → Knowledge Base → Service Health
      │                               │
      ▼                               ▼
Internet LLM → Web Search API    Notifications ("Luma Sleepy/Asleep")
      │                               │
      ▼                               ▼
      TTS → Audio Output → OBS Browser Source
      │
      ▼
Avatar (PNG / Live2D / 3D)
\`\`\`

**Celery Worker Services (Phase 1 Enhancement)**
- **Memory Processing Worker**: Background memory suggestion extraction and validation
- **Document Processing Worker**: Asynchronous document parsing and memory storage
- **LLM API Worker**: Rate-limited API calls with retry logic and fallback management
- **Token Usage Worker**: Background token tracking and aggregation
- **Celery Beat Scheduler**: Periodic tasks and scheduled operations

**Message Broker Infrastructure**
- **Redis**: Task queue and result backend for Celery workers
- **RabbitMQ**: Alternative message broker for production deployments

**Other Containers / Modules**
- ASR → microphone input  
- TTS → voice synthesis
- Internet LLM → web browsing & research
- Twitch chat listener → backend → Main LLM  
- Discord bot → backend modules
- GPU Monitor → Ollama hardware tracking
- Token Tracker → API usage monitoring

---

## Suggested Folder Structure

\`\`\`
project/
├─ backend/
│   ├─ app.py                    # FastAPI server
│   ├─ celery_app.py             # Celery application configuration
│   ├─ tasks.py                  # Celery task definitions
│   ├─ routers/
│   │   ├─ text_chat.py          # Phase 1: Text chat endpoints
│   │   ├─ voice.py              # Phase 2: ASR/TTS endpoints
│   │   ├─ vision.py             # Phase 4: Vision processing endpoints
│   │   ├─ memory.py             # Phase 1: Memory management endpoints
│   │   ├─ internet_search.py    # Phase 6: Web browsing endpoints
│   │   ├─ monitoring.py         # Phase 7-8: Token & GPU monitoring
│   │   ├─ twitch.py             # Phase 9: Twitch integration
│   │   ├─ avatar.py             # Phase 3: Avatar control
│   │   └─ discord.py            # Phase 10: Discord bot endpoints
│   ├─ models/
│   │   ├─ llm_interface.py      # Configurable LLM providers
│   │   ├─ memory_manager.py     # Memory operations
│   │   ├─ asr_wrapper.py        # Speech-to-text
│   │   ├─ tts_wrapper.py        # Text-to-speech
│   │   ├─ vision_wrapper.py     # Vision processing
│   │   ├─ internet_llm.py       # Web browsing LLM
│   │   └─ monitoring_service.py # Token & GPU tracking
│   ├─ utils/
│   │   ├─ api_limits.py         # API limit monitoring
│   │   ├─ gpu_monitor.py        # GPU usage tracking
│   │   ├─ cost_optimizer.py     # Provider switching logic
│   │   └─ notifications.py      # "Luma sleepy/asleep" alerts
│   ├─ config.py                 # Configuration management
│   └─ settings.py               # Model provider settings
├─ webapp/
│   ├─ src/
│   │   ├─ components/
│   │   │   ├─ ChatWindow.jsx        # Main chat interface
│   │   │   ├─ AvatarDisplay.jsx     # Phase 3: Avatar rendering
│   │   │   ├─ WebcamFeed.jsx        # Phase 4: Vision input
│   │   │   ├─ FeatureToggle.jsx     # Module enable/disable
│   │   │   ├─ MemoryPanel.jsx       # Phase 1: Memory management
│   │   │   ├─ MonitoringDashboard.jsx # Phase 7-8: Token & GPU monitoring
│   │   │   ├─ InternetSearch.jsx    # Phase 6: Web search interface
│   │   │   ├─ SettingsPage.jsx      # Comprehensive configuration
│   │   │   └─ Notifications.jsx     # API limit warnings
│   │   ├─ App.jsx
│   │   ├─ WebRTCManager.js        # Real-time audio/video
│   │   └─ api/                    # API client utilities
│   ├─ static/                     # Static assets
│   ├─ templates/                  # HTML templates
│   ├─ package.json
│   └─ docker-compose.yml
├─ docker-compose.yml
├─ Dockerfile.backend
├─ Dockerfile.webapp
├─ models/                         # AI model weights / API configs
├─ memory_db/                      # Vector DB / SQLite
├─ monitoring/                     # Monitoring services
│   ├─ gpu_monitor.py              # Ollama GPU tracking
│   ├─ token_tracker.py            # API usage monitoring
│   └─ health_check.py             # Service health monitoring
└─ docs/                           # Documentation
    ├─ api_endpoints.md            # API documentation
    ├─ model_configuration.md      # Provider setup guides
    └─ deployment_guide.md         # Deployment instructions
\`\`\`

---

## Next Steps
1. Implement **Phase 1**: text chat + hybrid memory panel ✅ **COMPLETE**  
2. Phase 2: ASR + TTS → real-time voice  
3. Phase 3: Avatar (PNG / Live2D / 3D)  
4. Phase 4: Vision integration (camera / screen)  
5. Phase 5: Optional Memory LLM  
6. Phase 6: Internet LLM Integration → web browsing & research capabilities  
7. Phase 7: API Limit Monitoring & Token Management → smart service management  
8. Phase 8: Advanced Monitoring Dashboard → GPU usage & system metrics  
9. Phase 9: OBS + Twitch Chat Integration → streaming capabilities  
10. Phase 10: Advanced Discord Bot Features → multi-speaker voice channels  

### Configuration Management
- Use **feature toggles** to enable/disable modules depending on hardware constraints  
- Start with **local models** and swap to **API-based models** for lower-resource setups  
- Configure **separate LLM providers** for each component (Main, Memory, Vision, Internet, Voice)
- Set up **API limit monitoring** with OpenRouter integration for free tier options
- Enable **GPU monitoring** for Ollama users to track hardware utilization

### Model Provider Selection
Each phase supports configurable model providers:
- **OpenRouter**: Unified API with free tier options for cost optimization
- **Local Models**: Ollama, DeepSeek, Qwen for offline operation
- **Cloud APIs**: OpenAI, Anthropic, Google for premium performance
- **Automatic Fallback**: Smart switching when limits are reached or services are unavailable

---

This Markdown document now serves as a **complete blueprint** for developing a multimodal AI VTuber / streamer / Discord bot with **OBS, Twitch, and Discord integration** and **toggleable modular design**.
