#!/bin/sh
set -e

echo "🔄 Running database migrations..."
if ! python run_migrations.py; then
    echo "❌ Database migrations failed. Exiting."
    exit 1
fi

echo "🚀 Starting bot..."
exec python bot.py
