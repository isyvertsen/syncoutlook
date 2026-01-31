#!/bin/bash
set -e

cd /app
exec python scheduler.py
