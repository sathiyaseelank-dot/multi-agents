# Chat Application Backend

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## API Endpoints

- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login
- POST `/api/auth/refresh` - Refresh access token
- GET `/api/auth/me` - Get current user
- POST `/api/auth/change-password` - Change password
- GET `/api/messages` - Get messages
- POST `/api/messages` - Create message
- DELETE `/api/messages/<id>` - Delete message
