# 💬 Real-Time Chat Application

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--Time-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A modern, feature-rich real-time chat application built with FastAPI, WebSockets, and PostgreSQL. Supports instant messaging, file sharing, typing indicators, and real-time user status tracking.

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Configuration](#%EF%B8%8F-configuration) • [Usage](#-usage) • [API Documentation](#-api-documentation)

</div>

---

## ✨ Features

### 🚀 Core Features
- **Real-Time Messaging** - Instant message delivery using WebSocket technology
- **User Authentication** - Secure JWT-based authentication system
- **Online Status Tracking** - Real-time user online/offline indicators
- **Message Status** - WhatsApp-style message status (Sent ✓, Delivered ✓✓, Read ✓✓)
- **Multi-Tab Support** - Seamless experience across multiple browser tabs
- **Typing Indicators** - Live "typing..." notifications
- **File Sharing** - Upload and share images and documents
- **Responsive Design** - Beautiful UI that works on all devices

### 📎 File Sharing
- **Supported Formats:**
  - Images: JPG, JPEG, PNG, GIF, WEBP
  - Documents: PDF, DOC, DOCX, TXT
- **File Size Limit:** 5MB per file
- **Features:**
  - Inline image previews
  - Document download cards
  - Upload progress indicators
  - Validation on both client and server

### 💬 Messaging Features
- One-on-one conversations
- Message history persistence
- Auto-scroll to latest messages
- Read receipts
- Timestamped messages
- Profile pictures support

### 🔐 Security Features
- JWT token authentication
- HTTP-only cookies
- WebSocket authentication
- User ID verification
- File upload validation
- SQL injection protection

---

## 🎬 Demo

### Chat Interface
```
┌─────────────────────────────────────────────────────┐
│  👤 John Doe                          [Logout]      │
├─────────────────────────────────────────────────────┤
│  🔍 Search or start new chat...                     │
├─────────────────────────────────────────────────────┤
│  👤 Alice Smith                            🟢       │
│  👤 Bob Johnson                            ⚫       │
│  👤 Carol White                            🟢       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  👤 Alice Smith                    🟢 Online        │
├─────────────────────────────────────────────────────┤
│                                                      │
│               Hey! How are you? ✓✓        10:30 AM │
│                                                      │
│  I'm doing great, thanks!  ✓✓              10:31 AM│
│                                                      │
│               typing...                             │
│                                                      │
├─────────────────────────────────────────────────────┤
│  📎  [Type a message...]              [Send ➤]      │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Python 3.9+** - Programming language
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Relational database
- **WebSockets** - Real-time bidirectional communication
- **JWT** - JSON Web Tokens for authentication
- **ImageKit** - Cloud-based image CDN and storage

### Frontend
- **HTML5** - Markup language
- **CSS3** - Styling with modern animations
- **JavaScript (ES6+)** - Client-side logic
- **WebSocket API** - Browser WebSocket implementation
- **Font Awesome** - Icon library

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher**
- **PostgreSQL 12 or higher**
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **ImageKit Account** (for file storage)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Neeraj-0217/real_time_chat_app.git
cd real_time_chat_app
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

**Option A: Using psql command line**

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE chat_app_db;

# Create user (optional)
CREATE USER chat_user WITH PASSWORD 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE chat_app_db TO chat_user;

# Exit
\q
```

**Option B: Using pgAdmin**

1. Open pgAdmin
2. Right-click on "Databases" → "Create" → "Database"
3. Enter database name: `chat_app_db`
4. Click "Save"

### 5. Set Up ImageKit Account

ImageKit is used for storing and serving uploaded files (images, documents).

1. **Sign Up:**
   - Go to [https://imagekit.io/](https://imagekit.io/)
   - Click "Sign Up" and create a free account

2. **Get API Credentials:**
   - After login, go to "Developer Options" in the dashboard
   - Copy the following:
     - **Public Key** (starts with `public_`)
     - **Private Key** (keep this secret!)
     - **URL Endpoint** (e.g., `https://ik.imagekit.io/your_id/`)

3. **Create Folders (Optional):**
   - In ImageKit dashboard, create folders:
     - `/chat_app_profiles/` (for profile pictures)
     - `/chat_app_images/` (for shared images)
     - `/chat_app_pdfs/` (for PDF files)
     - `/chat_app_documents/` (for documents)

---

## ⚙️ Configuration

### 1. Create .env File

Create a `.env` file in the project root directory:

```bash
# In the root directory
touch .env  # macOS/Linux
# or
type nul > .env  # Windows
```

### 2. Configure Environment Variables

Open `.env` file and add the following:

```env
# Application Settings
PROJECT_NAME=Real-Time Chat Application
PROJECT_VERSION=1.0.0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/chat_app_db

# ImageKit Configuration
IMAGEKIT_PUBLIC_KEY=your_imagekit_public_key
IMAGEKIT_PRIVATE_KEY=your_imagekit_private_key
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id/
```

### 3. Generate SECRET_KEY

For production, generate a secure SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and replace the SECRET_KEY value in `.env`

### 4. Update Database URL

Replace the database credentials in `DATABASE_URL`:

```
postgresql://username:password@host:port/database_name
```

Example:
```
postgresql://postgres:mypassword123@localhost:5432/chat_app_db
```

---

## 🗄️ Database Setup

### Create Tables

Run the following command to create all database tables:

```bash
python -c "from app.db.base import Base; from app.db.session import engine; Base.metadata.create_all(bind=engine)"
```

Or create a setup script `setup_db.py`:

```python
from app.db.base import Base
from app.db.session import engine
from app.db import models

def create_tables():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    create_tables()
```

Run it:
```bash
python setup_db.py
```

### Database Schema

The application uses the following tables:

**Users Table:**
```sql
- id (Primary Key)
- username (Unique)
- display_name
- gender
- profile_pic (URL)
- is_online (Boolean)
- created_at (Timestamp)
```

**Contacts Table:**
```sql
- id (Primary Key)
- owner_id (Foreign Key → users.id)
- contact_id (Foreign Key → users.id)
- added_at (Timestamp)
```

**Messages Table:**
```sql
- id (Primary Key)
- sender_id (Foreign Key → users.id)
- receiver_id (Foreign Key → users.id)
- content (Text)
- media_url (String, nullable)
- media_type (String: text/image/pdf/document)
- status (String: sent/delivered/read)
- timestamp (Timestamp)
```

---

## 🏃 Running the Application

### 1. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

### 3. Create First Account

1. Click "Create Account" on the login page
2. Fill in the registration form:
   - Username (unique identifier)
   - Display Name (your name)
   - Gender
   - Profile Picture (optional)
3. Click "Register"
4. Login with your username

### 4. Start Chatting

1. Search for users using the search bar
2. Click on a user to start chatting
3. Send messages, images, or documents
4. See real-time typing indicators
5. Watch message status update (✓ → ✓✓ → ✓✓)

---

## 📁 Project Structure

```
chat-application/
│
├── app/
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   └── security.py        # Authentication & JWT
│   │
│   ├── db/
│   │   ├── base.py            # SQLAlchemy base
│   │   ├── models.py          # Database models
│   │   └── session.py         # Database session
│   │
│   ├── routers/
│   │   ├── auth.py            # Authentication routes
│   │   ├── chat.py            # Chat & WebSocket routes
│   │   └── users.py           # User management
│   │
│   ├── schemas/
│   │   ├── message.py         # Message Pydantic schemas
│   │   └── user.py            # User Pydantic schemas
│   │
│   ├── services/
│   │   ├── image_service.py   # ImageKit integration
│   │   └── socket_manager.py  # WebSocket manager
│   │
│   ├── static/
│   │   └── js/
│   │       └── client_chat.js # Frontend JavaScript
│   │
│   ├── templates/
│   │   ├── auth/
│   │   │   ├── login.html     # Login page
│   │   │   └── register.html  # Registration page
│   │   └── chat/
│   │       └── dashboard.html # Chat interface
│   │
│   └── main.py                # FastAPI application entry
│
├── .env                       # Environment variables (create this)
├── .gitignore                # Git ignore file
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 📦 Dependencies

Create `requirements.txt` with the following:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
python-dotenv==1.0.0
jinja2==3.1.2
imagekitio==3.2.0
websockets==12.0
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration Options

### File Upload Settings

Edit `app/routers/chat.py`:

```python
# Maximum file size (in bytes)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
```

### Typing Indicator Timeout

Edit `app/static/js/client_chat.js`:

```javascript
// Time before typing indicator disappears (milliseconds)
typingTimeout = setTimeout(() => {
    // Stop typing
}, 3000);  // 3 seconds
```

### Token Expiration

Edit `.env`:

```env
# Token expires after 30 days (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=43200
```

---

## 🌐 API Documentation

### Authentication Endpoints

#### Register User
```http
POST /register
Content-Type: multipart/form-data

username: string
display_name: string
gender: string
profile_pic: file (optional)
```

#### Login
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username: string
```

#### Logout
```http
GET /logout
```

#### Verify Authentication
```http
GET /auth/verify
Authorization: Bearer <token>
```

### Chat Endpoints

#### Search Users
```http
GET /users/search?query=<search_term>
Authorization: Bearer <token>
```

#### Get Chat History
```http
GET /chat/history/{friend_id}
Authorization: Bearer <token>
```

#### Get User Status
```http
GET /user/status/{user_id}
Authorization: Bearer <token>
```

#### Upload File
```http
POST /upload/file
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: file
receiver_id: integer
```

### WebSocket Endpoint

```http
WS /ws/{client_id}?token=<jwt_token>
```

**Message Types:**

1. **Text Message:**
```json
{
    "receiver_id": 123,
    "content": "Hello!"
}
```

2. **Typing Indicator:**
```json
{
    "type": "typing",
    "receiver_id": 123,
    "is_typing": true
}
```

3. **Read Receipt:**
```json
{
    "type": "read_receipt",
    "message_id": 456,
    "sender_id": 789
}
```

4. **Delivered Receipt:**
```json
{
    "type": "delivered_receipt",
    "message_id": 456,
    "sender_id": 789
}
```

---

## 🧪 Testing

### Manual Testing Checklist

#### Authentication:
- [ ] Register new user
- [ ] Login with existing user
- [ ] Logout and verify session cleared
- [ ] Try accessing chat without login (should redirect)

#### Messaging:
- [ ] Send text message
- [ ] Receive message in real-time
- [ ] Verify message status (sent → delivered → read)
- [ ] Test with multiple tabs open
- [ ] Test message persistence (reload page)

#### Typing Indicators:
- [ ] Open 2 browsers with different users
- [ ] Type in one browser
- [ ] Verify "typing..." appears in other browser
- [ ] Stop typing and verify indicator disappears

#### File Sharing:
- [ ] Upload image (< 5MB)
- [ ] Upload PDF document
- [ ] Upload text file
- [ ] Try uploading file > 5MB (should fail)
- [ ] Try uploading .exe file (should fail)
- [ ] Verify inline image preview
- [ ] Download uploaded document

#### User Status:
- [ ] Login and verify "Online" status
- [ ] Close browser and verify "Offline" status
- [ ] Open multiple tabs (status should remain online)
- [ ] Close all tabs (status should go offline)

---

## 🐛 Troubleshooting

### Database Connection Error

**Error:** `could not connect to server: Connection refused`

**Solution:**
1. Check if PostgreSQL is running:
   ```bash
   # Windows
   services.msc
   
   # macOS
   brew services list
   
   # Linux
   sudo systemctl status postgresql
   ```
2. Verify DATABASE_URL in `.env`
3. Check PostgreSQL is listening on port 5432

### ImageKit Upload Error

**Error:** `Upload failed: 401 Unauthorized`

**Solution:**
1. Verify ImageKit credentials in `.env`
2. Check if keys have proper permissions
3. Ensure URL endpoint is correct (with trailing slash)

### WebSocket Connection Failed

**Error:** `WebSocket connection closed: 1008`

**Solution:**
1. Clear browser cookies
2. Logout and login again
3. Check if token is being sent correctly
4. Verify SECRET_KEY matches between sessions

### File Upload Not Working

**Error:** `File type not allowed`

**Solution:**
1. Check file extension is in allowed list
2. Verify file size is under 5MB
3. Check ImageKit account quota
4. Review browser console for errors

### Messages Not Appearing

**Solution:**
1. Check browser console for WebSocket errors
2. Verify both users are authenticated
3. Check network tab for failed requests
4. Ensure database connection is active

---

## 🚀 Deployment

### Production Checklist

#### 1. Environment Variables
```env
# Use strong, unique SECRET_KEY
SECRET_KEY=<generate-new-key-for-production>

# Use production database
DATABASE_URL=postgresql://user:pass@prod-host:5432/prod_db

# Use production ImageKit account
IMAGEKIT_PUBLIC_KEY=<prod-key>
IMAGEKIT_PRIVATE_KEY=<prod-key>
IMAGEKIT_URL_ENDPOINT=<prod-endpoint>
```

#### 2. Security Settings
- Enable HTTPS
- Set secure cookie flags
- Configure CORS properly
- Use environment-specific configs
- Enable rate limiting
- Add request size limits

#### 3. Database
- Use managed PostgreSQL (AWS RDS, Heroku Postgres)
- Set up regular backups
- Configure connection pooling
- Monitor query performance

#### 4. File Storage
- Upgrade ImageKit plan if needed
- Set up CDN caching
- Configure image optimization
- Monitor storage usage

#### 5. Server Configuration
```bash
# Production server with Gunicorn
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Deploy to Heroku

1. **Install Heroku CLI**
2. **Create Heroku app:**
   ```bash
   heroku create your-chat-app
   ```

3. **Add PostgreSQL:**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set IMAGEKIT_PUBLIC_KEY=your-key
   # ... set all other variables
   ```

5. **Create Procfile:**
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

6. **Deploy:**
   ```bash
   git push heroku main
   ```

### Deploy to AWS EC2

1. **Launch EC2 instance** (Ubuntu 22.04)
2. **SSH into server:**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-pip postgresql nginx
   ```

4. **Clone repository:**
   ```bash
   git clone your-repo-url
   cd chat-application
   ```

5. **Set up application:**
   ```bash
   pip3 install -r requirements.txt
   # Configure .env file
   # Set up PostgreSQL
   ```

6. **Configure Nginx:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
       }
   }
   ```

7. **Run with systemd:**
   Create `/etc/systemd/system/chatapp.service`
   ```ini
   [Unit]
   Description=Chat Application
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/chat-application
   ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

8. **Start service:**
   ```bash
   sudo systemctl start chatapp
   sudo systemctl enable chatapp
   ```

---

## 🔮 Future Improvements

### 📞 Voice & Video Chat

**Planned Features:**
- One-on-one voice calls
- Video calling with camera toggle
- Screen sharing capabilities
- Call history and logs
- Missed call notifications

**Technology Stack:**
- **WebRTC** for peer-to-peer connections
- **STUN/TURN servers** for NAT traversal
- **Socket.IO** for signaling
- **MediaRecorder API** for recording

**Implementation Steps:**
1. Integrate WebRTC library
2. Set up signaling server
3. Implement call initiation UI
4. Add audio/video controls
5. Handle call states (ringing, active, ended)
6. Store call history in database

**Challenges:**
- Bandwidth management
- Cross-browser compatibility
- NAT traversal issues
- Quality optimization

### 🤖 AI-Powered Features

#### 1. Smart Reply Suggestions
- Analyze message context
- Suggest 3-5 quick replies
- Learn from user patterns
- Multi-language support

**Tech:** GPT-4 API, Sentence transformers

#### 2. Message Translation
- Real-time translation
- Support 100+ languages
- Preserve formatting and emojis
- Translation confidence scores

**Tech:** Google Cloud Translation API

#### 3. Sentiment Analysis
- Detect message mood (positive/negative/neutral)
- Emoji suggestions based on sentiment
- Conflict detection in conversations
- Analytics dashboard

**Tech:** VADER Sentiment, TextBlob

#### 4. Smart Notifications
- Prioritize important messages
- Summarize long conversations
- Intelligent notification timing
- Do not disturb auto-detection

**Tech:** NLP classifiers, User behavior ML

#### 5. Chatbot Assistant
- Answer FAQs automatically
- Schedule meetings
- Set reminders
- Search conversation history
- Provide suggestions

**Tech:** LangChain, OpenAI GPT-4

#### 6. Content Moderation
- Detect inappropriate content
- Filter spam messages
- Block harmful links
- Report suspicious activity

**Tech:** Content Safety APIs, ML classifiers

#### 7. Voice-to-Text & Text-to-Voice
- Send voice messages as text
- Read messages aloud
- Multi-language support
- Accent detection

**Tech:** Google Speech-to-Text, Amazon Polly

#### 8. Image Recognition
- Auto-generate image captions
- Detect image content
- OCR for text in images
- Image moderation

**Tech:** Google Vision API, Tesseract OCR

### 📱 Additional Enhancements

#### Feature Wishlist:
- [ ] Group chats with admin controls
- [ ] Message reactions (❤️👍😂)
- [ ] Message editing & deletion
- [ ] Message forwarding
- [ ] @ mentions and replies
- [ ] Voice notes recording
- [ ] Location sharing
- [ ] Contact sharing
- [ ] Polls and surveys
- [ ] Custom themes/dark mode
- [ ] End-to-end encryption
- [ ] Two-factor authentication
- [ ] Email notifications
- [ ] Push notifications (PWA)
- [ ] Desktop app (Electron)
- [ ] Mobile apps (React Native)
- [ ] Export chat history
- [ ] Advanced search filters
- [ ] Message scheduling
- [ ] Automated backups
- [ ] Analytics dashboard
- [ ] Admin panel
- [ ] Rate limiting
- [ ] Content CDN integration
- [ ] Redis caching
- [ ] Load balancing
- [ ] Horizontal scaling

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Reporting Bugs
1. Check if the bug is already reported
2. Open a new issue with detailed description
3. Include steps to reproduce
4. Add screenshots if applicable

### Suggesting Features
1. Open an issue with [Feature Request] tag
2. Describe the feature and use case
3. Explain why it would be valuable

### Code Contributions
1. Fork the repository
2. Create a feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Make your changes
4. Write tests if applicable
5. Commit your changes
   ```bash
   git commit -m "Add amazing feature"
   ```
6. Push to the branch
   ```bash
   git push origin feature/amazing-feature
   ```
7. Open a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Write docstrings for functions
- Keep functions small and focused

---

## 📄 License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👥 Authors

- **Neeraj Kumar** - *Initial work* - [YourGitHub](https://github.com/Neeraj-0217)

---

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- SQLAlchemy for the powerful ORM
- ImageKit for file storage and CDN
- Font Awesome for the beautiful icons
- The open-source community for inspiration

---

## 📞 Support

Having trouble? Here's how to get help:

- 📧 **Email:** neerajbauri02@zohomail.in
- 🐛 **LinkedIn:** [LinkedIn](www.linkedin.com/in/neeraj-kumar-02nrj25)

---

## ⭐ Star This Repository

If you find this project useful, please consider giving it a star! It helps others discover the project and motivates continued development.

---

<div align="center">

**Made with ❤️ and Python**

[⬆ Back to Top](#-real-time-chat-application)

</div>
