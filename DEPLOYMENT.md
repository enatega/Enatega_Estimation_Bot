# Deployment Guide - Railway

## Quick Deploy to Railway

### Prerequisites
1. Railway account (https://railway.app)
2. OpenAI API key
3. GitHub account (optional, for CI/CD)

### Step 1: Prepare Environment Variables

Create a `.env` file locally (for testing) or set in Railway dashboard:

```bash
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_HOURLY_RATE=100.0
BUFFER_PERCENTAGE=0.20
OPENAI_MODEL=gpt-4-turbo-preview
```

### Step 2: Deploy to Railway via GitHub

#### Option A: Via Railway Dashboard (Recommended)
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select the repository
5. Railway will automatically detect the Dockerfile
6. Set environment variables in the dashboard (see Step 3)
7. Deploy!

#### Option B: Via Railway CLI
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to GitHub repo (if not already linked)
railway link

# Deploy
railway up
```

**Note:** Railway will use the Dockerfile for building and deployment.

### Step 3: Configure Environment Variables

In Railway dashboard:
1. Go to your project → Variables
2. Add:
   - `OPENAI_API_KEY` (required)
   - `DEFAULT_HOURLY_RATE` (optional, default: 100.0)
   - `BUFFER_PERCENTAGE` (optional, default: 0.20)
   - `OPENAI_MODEL` (optional, default: gpt-4-turbo-preview)

### Step 4: Verify Deployment

Once deployed, Railway will provide a URL. Test endpoints:

```bash
# Health check
curl https://your-app.railway.app/api/v1/health

# Get features
curl https://your-app.railway.app/api/v1/features

# Create estimate
curl -X POST https://your-app.railway.app/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"requirements": "I need a client onboarding system with user authentication and dashboard"}'
```

### Step 5: API Documentation

Access interactive API docs at:
- Swagger UI: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc`

## Local Development

### Setup
```bash
# Virtual environment is already created
# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
# Edit .env and add your OPENAI_API_KEY
# The .env file is already created, just update OPENAI_API_KEY

# Run locally
uvicorn app.main:app --reload
```

### Using Docker Locally (Optional)
```bash
# Build Docker image
docker build -t estimation-bot .

# Run container
docker run -p 8000:8000 --env-file .env estimation-bot
```

### Test Endpoints Locally
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create estimate
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"requirements": "User authentication and dashboard"}'
```

## API Endpoints

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
  "breakdown": [...],
  "assumptions": [...],
  "timeline": "Approximately 6 weeks",
  "summary": "...",
  "next_steps": [...]
}
```

### POST `/api/v1/chat`
Chat endpoint for conversational interaction.

**Request:**
```json
{
  "message": "What would it cost to build a client onboarding system?",
  "conversation_history": []
}
```

### GET `/api/v1/features`
Get list of available features.

### GET `/api/v1/health`
Health check endpoint.

## Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   - Ensure `OPENAI_API_KEY` is set in Railway environment variables
   - Check API key is valid and has credits

2. **PDF Extraction Fails**
   - Ensure all PDF files are in the project root
   - Check file permissions

3. **Port Issues**
   - Railway sets `$PORT` automatically
   - Dockerfile uses `${PORT:-8000}` for fallback
   - Don't hardcode port numbers

4. **Docker Build Fails**
   - Ensure Dockerfile is in project root
   - Check that all files are committed to GitHub
   - Review Railway build logs for specific errors

4. **Import Errors**
   - Ensure all dependencies are in `requirements.txt`
   - Check Python version matches `runtime.txt`

## Monitoring

Railway provides:
- Logs dashboard
- Metrics and monitoring
- Automatic deployments on git push (if connected to GitHub)

## Support

For issues:
1. Check Railway logs
2. Review API documentation at `/docs`
3. Test endpoints locally first
4. Check environment variables
