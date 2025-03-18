#!/bin/sh
sleep 5  # Даём время PostgreSQL полностью подняться
exec uvicorn main:app --host 0.0.0.0 --port 8000 