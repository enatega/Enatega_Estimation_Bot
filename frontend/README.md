# Frontend - Estimation Bot

Simple, modern frontend for testing the Estimation Bot API.

## Features

- ✅ **Estimate Generation** - Get detailed time and cost estimates
- ✅ **Chat Interface** - Conversational interaction with the bot
- ✅ **Responsive Design** - Works on desktop and mobile
- ✅ **Real-time Updates** - See estimates as they're generated

## Usage

### Option 1: Serve via FastAPI (Recommended)

The FastAPI server automatically serves the frontend at the root URL:

```bash
# Start the server
uvicorn app.main:app --reload

# Open browser to http://localhost:8000
```

### Option 2: Serve with Python HTTP Server

```bash
cd frontend
python3 -m http.server 8080
# Open browser to http://localhost:8080
```

### Option 3: Open Directly

Simply open `index.html` in your browser (API URL will need to be set correctly).

## Configuration

Update the API URL in the input field or change the default in `app.js`:

```javascript
let API_BASE_URL = 'http://localhost:8000';  // Local
// or
let API_BASE_URL = 'https://your-app.railway.app';  // Production
```

## Files

- `index.html` - Main HTML structure
- `styles.css` - Styling and layout
- `app.js` - JavaScript logic and API integration
