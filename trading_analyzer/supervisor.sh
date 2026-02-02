#!/bin/bash
# Auto-restart bot supervisor
cd /home/user/Claude-code/trading_analyzer

while true; do
    echo "$(date): Starting bot..."
    python3 -u bot.py 2>&1 | tee -a bot.log
    echo "$(date): Bot crashed. Restarting in 5 seconds..."
    sleep 5
done
