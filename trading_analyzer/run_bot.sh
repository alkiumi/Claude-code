#!/bin/bash
# Bot Watchdog - Auto-restart on crash
cd /home/user/Claude-code/trading_analyzer

echo "🤖 Starting Trading Bot Watchdog..."
echo "Press Ctrl+C to stop"

while true; do
    echo "$(date): Starting bot..."
    python3 -u bot.py 2>&1 | tee -a bot.log

    EXIT_CODE=$?
    echo "$(date): Bot exited with code $EXIT_CODE"

    echo "$(date): Waiting 10 seconds before restart..."
    sleep 10

    echo "$(date): Restarting bot..."
done
