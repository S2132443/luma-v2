# Luma v2

A containerized Discord bot with web dashboard for monitoring and control.

## Features

- Discord bot with /chat command using DeepSeek API
- Web dashboard to view token usage, message logs, input API keys, control bot personality
- Short-term and long-term memory per user
- Containerized with Docker Compose

## Setup

1. Clone the repo
2. Run `docker-compose up --build`
3. Access dashboard at http://localhost:5000
4. Configure API keys and personality in Settings
5. Invite bot to Discord server and use /chat

## Architecture

- Bot: Python, discord.py, OpenAI API for DeepSeek
- Webapp: Flask, Jinja templates
- DB: PostgreSQL
