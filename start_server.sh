#!/bin/bash
.venv/bin/uvicorn server.search_service:app --reload --host 0.0.0.0 --port 8000
