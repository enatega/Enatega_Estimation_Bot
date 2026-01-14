# Quick Start Guide

## Start the Server

### Option 1: Using the Start Script (Recommended)
```bash
./start_server.sh
```

### Option 2: Manual Start
```bash
# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn app.main:app --reload
```

### Option 3: Using Python Module
```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

## Access Points

Once the server is running:

- **Frontend:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic_settings'"

**Solution:** Make sure you're using the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Wrong Python Version

If you see Python 3.12 errors but venv has 3.8:
```bash
# Deactivate and reactivate
deactivate
source venv/bin/activate
which python  # Should show venv/bin/python
```

### Port Already in Use

```bash
# Use a different port
uvicorn app.main:app --port 8001 --reload
```

## Environment Variables

Make sure `.env` file has:
- `OPENAI_API_KEY` - Your OpenAI API key
- `QDRANT_URL` - Your Qdrant Cloud URL (optional)
- `QDRANT_API_KEY` - Your Qdrant API key (optional)

## Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get estimate
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"requirements": "User authentication and dashboard"}'
```

## Frontend Testing

1. Start the server
2. Open browser to http://localhost:8000
3. Enter requirements and click "Get Estimate"
4. Or try "Chat Mode" for conversational interaction
