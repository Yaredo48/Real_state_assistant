#!/usr/bin/env python
"""
Development server runner.
File: backend/run.py
"""

import uvicorn
import argparse
from app.core.config import settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DealLens AI development server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📡 Server will run on http://{args.host}:{args.port}")
    print(f"📚 API Docs: http://{args.host}:{args.port}{settings.API_PREFIX}/docs")
    print(f"⚙️  Environment: {settings.ENVIRONMENT}")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if settings.DEBUG else "info"
    )