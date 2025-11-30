
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
- **Task Queue (optional):** Celery / RQ for async tasks  
- **Database / Memory:**  
  - Short-term memory: in-memory dict / Redis  
  - Long-term memory: Vector DB (ChromaDB, Weaviate) + SQLite fallback  

### Frontend
- **Framework:** React / Solid / Vue  
- **Components:**  
  - Chat window (text + TTS messages)  
  - Feature toggles: See / Hear / Speak / Memory / Twitch  
  - Webcam / screen share feed  
  - Avatar display (PNG / Live2D / 3D)  
  - Audio playback / microphone capture  

### AI Models
| Module | Local Option | API Option |
|--------|-------------|------------|
| Main LLM | DeepSeek V3, Qwen 7B | OpenAI GPT-4o, Claude 3 |
| Vision LLM | Qwen-VL 7B, MiniGPT-4 | GPT-4o Vision API, Claude Vision |
| TTS | Kokoro, DIA 1.6B | ElevenLabs, Google TTS |
| ASR | Whisper.cpp, Faster-whisper | OpenAI Whisper API, Deepgram |
| Memory LLM | Phi-3 Mini, Qwen 1.8B | GPT-3.5 Mini / API |

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

### Phase 6: OBS + Twitch Chat Integration
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

### Phase 7: Discord Bot
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
┌─────────────────────────────┐
│          Frontend           │
│ Chat + Avatar + Webcam + OBS│
└─────────────┬──────────────┘
              │ WebSocket / WebRTC
              ▼
┌─────────────────────────────┐
│          Backend            │
│ FastAPI / Feature Flags     │
└─────┬───────┬───────────────┘
      │       │
      ▼       ▼
Main LLM   Vision LLM (optional)
      │
      ▼
Optional Memory LLM → Knowledge Base
      │
      ▼
      TTS → Audio Output → OBS Browser Source
      │
      ▼
Avatar (PNG / Live2D / 3D)
\`\`\`

**Other Containers / Modules**
- ASR → microphone input  
- Twitch chat listener → backend → Main LLM  
- Discord bot → backend modules  

---

## Suggested Folder Structure

\`\`\`
project/
├─ backend/
│   ├─ app.py            # FastAPI server
│   ├─ routers/
│   │   ├─ text_chat.py
│   │   ├─ voice.py
│   │   ├─ vision.py
│   │   ├─ memory.py
│   │   ├─ twitch.py
│   │   └─ avatar.py
│   ├─ models/           # LLM, Memory, ASR, TTS wrappers
│   ├─ utils/
│   └─ config.py
├─ webapp/
│   ├─ src/
│   │   ├─ components/
│   │   │   ├─ ChatWindow.jsx
│   │   │   ├─ AvatarDisplay.jsx
│   │   │   ├─ WebcamFeed.jsx
│   │   │   └─ FeatureToggle.jsx
│   │   ├─ App.jsx
│   │   └─ WebRTCManager.js
│   └─ package.json
├─ docker-compose.yml
├─ Dockerfile.backend
├─ Dockerfile.webapp
├─ models/               # AI model weights / API configs
└─ memory_db/            # Vector DB / SQLite
\`\`\`

---

## Next Steps
1. Implement **Phase 1**: text chat + hybrid memory panel  
2. Phase 2: ASR + TTS → real-time voice  
3. Phase 3: Avatar (PNG / Live2D / 3D)  
4. Phase 4: Vision integration (camera / screen)  
5. Phase 5: Optional Memory LLM  
6. Phase 6: OBS + Twitch chat  
7. Phase 7: Discord bot integration  

- Use **feature toggles** to enable/disable modules depending on hardware constraints  
- Start with **local models** and swap to **API-based models** for lower-resource setups  

---

This Markdown document now serves as a **complete blueprint** for developing a multimodal AI VTuber / streamer / Discord bot with **OBS, Twitch, and Discord integration** and **toggleable modular design**.