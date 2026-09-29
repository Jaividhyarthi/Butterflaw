#!/usr/bin/env bash
set -e
pip install -q -r requirements.txt
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
