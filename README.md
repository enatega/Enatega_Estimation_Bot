# Client Onboarding System - Estimation Bot API

## 🚀 Overview

A production-ready FastAPI backend that provides intelligent time and cost estimates for client onboarding systems. Uses OpenAI GPT-4 to generate ChatGPT-like responses based on client requirements.

## ✨ Features

- **AI-Powered Estimation:** Uses OpenAI GPT-4 to extract features and generate estimates
- **Natural Language Processing:** Understands client requirements in plain English
- **ChatGPT-like Responses:** Generates professional, detailed responses matching example format
- **Comprehensive Breakdowns:** Feature-by-feature time and cost estimates
- **RESTful API:** Clean, documented API endpoints ready for frontend integration
- **Railway Ready:** Pre-configured for one-click deployment on Railway

## 📁 Project Structure

```
Estimate_Bot/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Configuration
│   ├── models/            # Pydantic schemas
│   ├── services/          # Business logic
│   │   ├── estimation_engine.py
│   │   ├── knowledge_base.py
│   │   └── openai_service.py
│   ├── utils/            # Utilities (PDF extraction)
│   └── main.py           # FastAPI app
├── requirements.txt       # Python dependencies
├── Procfile              # Railway deployment config
├── railway.json          # Railway config
├── DEPLOYMENT.md         # Deployment guide
└── .env.example          # Environment variables template
```

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone and navigate
cd Estimate_Bot

# 2. Activate virtual environment (already created)
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
# Edit .env and add your OPENAI_API_KEY
# The .env file is already created

# 5. Run the server
uvicorn app.main:app --reload
```

### Using Docker Locally (Optional)
```bash
# Build and run with Docker
docker build -t estimation-bot .
docker run -p 8000:8000 --env-file .env estimation-bot
```

API will be available at `http://localhost:8000`

### Deploy to Railway

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick Deploy:**
1. Push code to GitHub
2. Connect Railway to your GitHub repository
3. Railway will auto-detect Dockerfile
4. Set `OPENAI_API_KEY` environment variable in Railway dashboard
5. Deploy!

## 📡 API Endpoints

### POST `/api/v1/estimate`
Generate time and cost estimate.

**Request:**
```json
{
  "requirements": "I need a client onboarding system with user authentication, dashboard, and payment processing",
  "hourly_rate": 100.0,
  "include_breakdown": true
}
```

**Response:**
```json
{
  "total_time_hours": 240.0,
  "total_cost": 24000.0,
  "breakdown": [
    {
      "feature": "User Authentication",
      "time_hours": 52.0,
      "cost": 5200.0,
      "complexity": "medium"
    }
  ],
  "assumptions": [...],
  "timeline": "Approximately 6 weeks",
  "summary": "AI-generated summary...",
  "next_steps": [...]
}
```

### POST `/api/v1/chat`
Chat endpoint for conversational interaction.

### GET `/api/v1/features`
Get list of available features.

### GET `/api/v1/health`
Health check endpoint.

**Interactive API Docs:** Visit `/docs` for Swagger UI or `/redoc` for ReDoc.

## 🔧 Configuration

### Environment Variables

```bash
OPENAI_API_KEY=your_key_here          # Required
DEFAULT_HOURLY_RATE=100.0             # Optional
BUFFER_PERCENTAGE=0.20                # Optional
OPENAI_MODEL=gpt-4-turbo-preview      # Optional
```

### Default Settings

- **Hourly Rate:** $100/hour
- **Buffer:** 20%
- **Model:** GPT-4 Turbo Preview
- **Temperature:** 0.7

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get features
curl http://localhost:8000/api/v1/features

# Create estimate
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": "User authentication and dashboard"
  }'
```

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Railway deployment guide
- **[PROJECT_WORKFLOW.md](PROJECT_WORKFLOW.md)** - Complete project workflow
- **API Docs** - Available at `/docs` when server is running

## 🛠️ Technology Stack

- **Framework:** FastAPI
- **AI:** OpenAI GPT-4 API
- **Vector Database:** Qdrant (in-memory or Qdrant Cloud)
- **Embeddings:** Sentence Transformers (all-MiniLM-L6-v2)
- **PDF Processing:** pdfplumber, PyPDF2
- **DOCX Processing:** python-docx
- **Validation:** Pydantic
- **Deployment:** Railway (Docker)
- **Frontend:** Vanilla HTML/CSS/JS (included)

## 📝 Notes

- The system extracts features from client requirements using AI
- Estimates include a 20% buffer for unforeseen complexities
- All responses are formatted to match ChatGPT example style
- Knowledge base is built from provided PDF/DOCX documents

## 🔐 Security

- API keys stored in environment variables
- CORS configured for frontend integration
- Input validation via Pydantic schemas
- Error handling and logging included

## 📞 Support

For deployment issues, see [DEPLOYMENT.md](DEPLOYMENT.md).  
For API usage, check `/docs` endpoint when server is running.
