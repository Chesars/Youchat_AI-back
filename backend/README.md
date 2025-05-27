# YouChat AI Backend

## Environment Setup

Create a `.env` file in the backend directory with the following variables:

```env
# Google Gemini API Key (Required)
API_KEY=your_gemini_api_key_here

# Optional: Port configuration (default is 8000)
PORT=8000
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn main:app --reload
```

## Deployment

This project is configured for deployment on Render. Make sure to:
1. Set up your environment variables in the Render dashboard
2. Connect your GitHub repository
3. Deploy using the provided `render.yaml` configuration 