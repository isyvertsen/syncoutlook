#!/bin/bash
set -e

cd /app
exec /opt/venv/bin/python scheduler.py
