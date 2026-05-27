# 💠 Gemini Nexus System

<div align="center">

# The Gemini-to-OpenAI API Proxy

### Advanced Stealth Reverse Proxy for Google Gemini Web UI

Convert Google's Gemini Web Interface into a fully OpenAI-compatible REST API with persistent conversations, Telegram administration, TLS impersonation, image support, and production-grade scalability.

<br>

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-green?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker)
![SQLite](https://img.shields.io/badge/SQLite-Integrated-lightgrey?style=for-the-badge&logo=sqlite)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

# 📚 Table of Contents

- [✨ Overview](#-overview)
- [🚀 Key Features](#-key-features)
- [🧠 Deep Architecture](#-deep-architecture)
- [⚡ How Gemini Nexus Works](#-how-gemini-nexus-works)
- [🔐 Authentication System](#-authentication-system)
- [🍪 Cookie Auto Extraction](#-cookie-auto-extraction)
- [🔄 Auto Cookie Rotation](#-auto-cookie-rotation)
- [🧬 OpenAI Compatibility Layer](#-openai-compatibility-layer)
- [🖼️ Multimodal Support](#️-multimodal-support)
- [📋 Requirements](#-requirements)
- [🚀 Installation Guide](#-installation-guide)
- [🐳 Docker Deployment](#-docker-deployment)
- [⚙️ Environment Variables](#️-environment-variables)
- [🤖 Telegram Bot System](#-telegram-bot-system)
- [📡 API Examples](#-api-examples)
- [💻 Web UI](#-web-ui)
- [📂 Repository Structure](#-repository-structure)
- [🛡️ Security & Stealth](#️-security--stealth)
- [📈 Performance](#-performance)
- [🧩 Technology Stack](#-technology-stack)
- [⚠️ Disclaimer](#️-disclaimer)
- [📜 License](#-license)

---

# ✨ Overview

Gemini Nexus is a high-performance stealth proxy that converts Google's Gemini Web UI into a fully OpenAI-compatible REST API server.

The project is designed to bridge the gap between:

- Google's free Gemini models
- OpenAI SDK ecosystem
- LangChain
- AutoGPT
- AI Agents
- Telegram bots
- Web dashboards
- Custom applications

Unlike traditional wrappers, Gemini Nexus is built as a complete production architecture.

It includes:

- OpenAI schema translation
- Session persistence
- Cookie automation
- TLS impersonation
- Telegram administration
- SQLite conversation memory
- Streaming support
- Image handling
- Docker deployment
- Auto-healing cookie refresh systems

---

# 🚀 Key Features

| Feature | Description |
|---|---|
| 🔄 OpenAI Compatibility | Full support for `/v1/chat/completions` and `/v1/models` |
| ⚡ Streaming Responses | Real-time token streaming support |
| 🧠 Stateful Conversations | Persistent memory with conversation tracking |
| 🍪 Cookie Automation | Browser cookie extraction and rotation |
| 🤖 Telegram Admin Bot | Remote server management |
| 🖼️ Image Upload Support | Upload images directly to Gemini |
| 💻 Monaco Editor UI | Professional browser interface |
| 🐳 Docker Support | Containerized deployment |
| 🔐 API Key Management | Multi-user API authentication |
| 🛡️ TLS Impersonation | Chrome-grade fingerprint spoofing |
| 📡 Proxy Support | SOCKS5 and HTTP proxy support |
| 🏥 Auto-Healing System | Automatic cookie refresh endpoints |
| 📁 SQLite Database | Persistent lightweight storage |
| 🌐 Multi-Model Support | Gemini Flash / Pro / Thinking models |

---

# 🧠 Deep Architecture

```text
                           ┌────────────────────┐
                           │ OpenAI Applications│
                           │ LangChain / SDKs   │
                           └─────────┬──────────┘
                                     │
                                     ▼
                     ┌────────────────────────────┐
                     │      FastAPI Backend       │
                     │  OpenAI-Compatible Routes  │
                     └─────────────┬──────────────┘
                                   │
                                   ▼
                     ┌────────────────────────────┐
                     │     Gemini Core Engine     │
                     │ Conversation Management    │
                     └─────────────┬──────────────┘
                                   │
                                   ▼
                     ┌────────────────────────────┐
                     │        curl_cffi           │
                     │  TLS Browser Impersonation │
                     └─────────────┬──────────────┘
                                   │
                                   ▼
                     ┌────────────────────────────┐
                     │    Google Gemini Web UI    │
                     └────────────────────────────┘
```

---

# ⚡ How Gemini Nexus Works

Google actively blocks automated traffic using advanced techniques like:

- TLS fingerprint analysis
- Behavioral analysis
- Header validation
- Browser signature inspection
- Connection fingerprinting

Traditional Python libraries such as:

```python
requests
aiohttp
httpx
```

are easily detected by Google's infrastructure.

Gemini Nexus bypasses these protections using:

```python
from curl_cffi.requests import AsyncSession
```

which impersonates the exact TLS fingerprints of a real Chrome browser.

---

# 🔐 Authentication System

Gemini Nexus authenticates using real Google session cookies.

Required cookies:

```text
__Secure-1PSID
__Secure-1PSIDTS
```

These cookies are extracted from your logged-in Gemini browser session.

---

# 🍪 Cookie Auto Extraction

One of the most advanced features of Gemini Nexus is automatic browser cookie extraction.

The project uses:

```python
import browser_cookie3
```

to directly access browser cookie databases.

Supported browsers include:

- Chrome
- Edge
- Brave
- Opera
- Firefox
- Chromium
- Vivaldi
- Safari
- LibreWolf

---

## Auto Cookie Workflow

```text
User Logged Into Gemini
            │
            ▼
 browser_cookie3 scans browser
            │
            ▼
 Extract __Secure-1PSID
 Extract __Secure-1PSIDTS
            │
            ▼
 Inject into AsyncSession
            │
            ▼
 Authenticated Gemini Access
```

---

## Actual Cookie Extraction Logic

```python
if auto_cookie:
    extractor = CookieExtractor()
    cookie_data = extractor.extract_cookies(save_to_disk=False)

    self.secure_1psid = cookie_data['__Secure-1PSID']
    self.secure_1psidts = cookie_data['__Secure-1PSIDTS']
```

---

## Browser Extraction Engine

```python
for browser_fn in SUPPORTED_BROWSERS:
    cj = browser_fn(domain_name=domain)
```

The project loops through all installed browsers until valid Google cookies are found.

---

# 🔄 Auto Cookie Rotation

Gemini Nexus also supports automatic cookie refresh.

When `__Secure-1PSIDTS` becomes outdated, the system can request a fresh cookie using:

```text
https://accounts.google.com/RotateCookies
```

---

## Cookie Rotation Logic

```python
async def __rotate_cookies(self):
```

This allows the system to survive temporary cookie refreshes without requiring manual login again.

---

# 🧬 OpenAI Compatibility Layer

Gemini Nexus converts OpenAI requests into Gemini WebUI requests.

Incoming request:

```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ]
}
```

gets transformed internally into Gemini request structures.

---

## Supported Endpoints

| Endpoint | Description |
|---|---|
| `/v1/chat/completions` | Chat completion API |
| `/v1/models` | Available models |
| `/v1/admin/cookies` | Cookie auto-healing |
| `/health` | Diagnostics |

---

# 🖼️ Multimodal Support

Gemini Nexus supports:

- Image uploads
- Image parsing
- Generated image extraction
- Multimodal prompts

---

## Example

```python
response = chatbot.ask(
    "Describe this image",
    image="cat.png"
)
```

---

# 📋 Requirements

## Required

- Python 3.10+
- Google account
- Telegram account
- Telegram bot token
- Telegram user ID

## Optional

- Docker
- VPS server
- SOCKS5 proxy
- Reverse proxy

---

# 🚀 Installation Guide

---

## 1. Clone Repository

```bash
git clone https://github.com/Animeki004/Gemini-Chat-API.git
cd Gemini-Chat-API
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create `.env`

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
PORT=8000
```

---

## 5. Start Server

```bash
python main.py
```

---

# 🐳 Docker Deployment

---

## Build Image

```bash
docker build -t gemini-nexus .
```

---

## Run Container

```bash
docker run -d \
-p 8000:8000 \
-v $(pwd)/data:/app/data \
--env-file .env \
--name gemini-nexus \
gemini-nexus
```

---

# ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `ADMIN_ID` | Telegram administrator ID |
| `PORT` | FastAPI server port |
| `DEBUG` | Debug logging |
| `PROXY` | Optional proxy URL |

---

# 🤖 Telegram Bot System

The Telegram bot acts as the remote administration panel for the server.

Only the configured admin can execute commands.

---

## Available Commands

| Command | Description |
|---|---|
| `/start` | Show help |
| `/help` | Documentation |
| `/chat` | Direct Gemini chat |
| `/end` | Exit chat |
| `/setcookies` | Update Google cookies |
| `/newkey` | Generate API key |
| `/newadminkey` | Generate admin key |
| `/listkeys` | View active keys |
| `/settimeout` | Set conversation timeout |
| `/revoke` | Revoke API key |
| `/models` | Show available models |
| `/health` | Diagnostics |
| `/backup` | Download database backup |

---

# 📡 API Examples

---

## cURL Example

```bash
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer sk-your-api-key" \
-d '{
  "model": "gemini-1.5-pro",
  "messages": [
    {
      "role": "user",
      "content": "Explain quantum computing."
    }
  ]
}'
```

---

## Python Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-api-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gemini-1.5-pro",
    messages=[
        {
            "role": "user",
            "content": "Write a Fibonacci script"
        }
    ]
)

print(response.choices[0].message.content)
```

---

## JavaScript Example

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "sk-your-api-key",
  baseURL: "http://localhost:8000/v1"
});

const response = await client.chat.completions.create({
  model: "gemini-1.5-pro",
  messages: [
    {
      role: "user",
      content: "Hello Gemini"
    }
  ]
});

console.log(response.choices[0].message.content);
```

---

# 💻 Web UI

Gemini Nexus includes a Monaco-powered frontend interface.

Features:

- Dark mode
- Syntax highlighting
- Code formatting
- Persistent chat
- Copy-to-clipboard
- Responsive layout

Open:

```text
index.html
```

in your browser.

---

# 📂 Repository Structure

```text
GEMINI-CHAT-API/
│
├── data/
│   ├── database.db
│   └── telegram_sessions.json
│
├── gemini_client/
│   ├── __init__.py
│   ├── constants.py
│   ├── cookie_manager.py
│   ├── core.py
│   ├── enums.py
│   ├── images.py
│   └── utils.py
│
├── legacy/
│
├── admin_bot.py
├── api.py
├── database.py
├── Dockerfile
├── index.html
├── LICENSE
├── main.py
├── README.md
├── requirements.txt
└── test.py
```

---

# 🛡️ Security & Stealth

Gemini Nexus focuses heavily on stealth networking.

Security mechanisms include:

- TLS impersonation
- Browser-identical headers
- Real browser cookies
- Proxy support
- Session rotation
- Admin verification
- SQLite isolation

---

# 📈 Performance

## Recommended Specifications

| Usage | RAM | CPU |
|---|---|---|
| Personal | 1 GB | 1 Core |
| Small Team | 2 GB | 2 Cores |
| Heavy Usage | 4 GB+ | 4 Cores |

---

## Performance Optimizations

- Async networking
- Connection pooling
- Streaming responses
- TLS session reuse
- SQLite persistence
- Lightweight architecture

---

# 🧩 Technology Stack

| Technology | Purpose |
|---|---|
| FastAPI | API backend |
| curl_cffi | TLS impersonation |
| SQLite | Database |
| asyncio | Async execution |
| Telegram Bot API | Remote management |
| Docker | Deployment |
| Monaco Editor | Frontend |

---

# ⚠️ Disclaimer

> Educational Purposes Only.

This project is unofficial and is not affiliated with:

- Google LLC
- OpenAI

This repository exists for:
- reverse engineering research
- API interoperability research
- networking research
- TLS fingerprinting studies

Using automation against web interfaces may violate Terms of Service.

Use responsibly.

---

# 📜 License

Licensed under the MIT License.

See:

```text
LICENSE
```

for details.

---

# ❤️ Credits

Inspired by:

- OEvortex/Gemini-Chat-API

Enhanced and expanded by:

- Animeki004

---

# 🌟 Final Notes

Gemini Nexus is designed to provide:

- OpenAI compatibility
- stealth networking
- production architecture
- scalable deployments
- persistent memory
- enterprise-grade infrastructure

while maintaining a clean developer experience.

---

<div align="center">

# 🚀 Gemini Nexus

### Bridging Gemini and OpenAI Ecosystems

⭐ Star the repository if you found it useful.

</div>