# AI Chat Assistant Project

## Overview
Modern AI chat interface powered by LLaMA 3, featuring multiple AI personalities, subscription plans, and a user-friendly interface.

## Project Structure
```
│
├── index.html               ← Landing page (introduce AI, link to chat)
├── chat.html               ← Chat page (AI interface, personality toggle)
├── subscription.html       ← Subscription/paywall page
├── README.md              ← This file
├── .env                   ← Secrets / API keys
├── assets/               ← Images, icons
│   └── logo.png
├── data/                 ← Database folder
│   └── database.db       ← SQLite database for users & sessions
└── py_system/           ← All Python backend files
    ├── server.py        ← Flask backend serving chat & pages
    ├── utils.py         ← Helper functions
    └── ai_model.py      ← AI integration (LLaMA 3)
```

## Features
- Modern, responsive UI
- Multiple AI personalities
- Real-time chat interface
- User authentication
- Subscription plans
- Session management
- SQLite database
- LLaMA 3 integration (placeholder)

## Setup & Installation
1. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```
   FLASK_SECRET_KEY=your_secret_key
   LLAMA_API_KEY=your_api_key
   DATABASE_PATH=data/database.db
   ```

3. Initialize the database:
   ```bash
   python py_system/server.py init-db
   ```

4. Run the server:
   ```bash
   python py_system/server.py
   ```

## Development
- Frontend: HTML5, CSS3, JavaScript
- Backend: Python Flask
- Database: SQLite
- AI: LLaMA 3 integration

## API Endpoints
- `/api/chat`: Chat messages
- `/api/auth`: Authentication
- `/api/subscribe`: Subscription management

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License
MIT License