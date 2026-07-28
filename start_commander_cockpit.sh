#!/bin/zsh
cd "$(dirname "$0")"
mkdir -p logs
python3 commander_cpu.py >> logs/cpu.log 2>&1 &
CPU=$!
python3 chart_server.py >> logs/chart.log 2>&1 &
CHART=$!
echo "$CPU $CHART" > .cockpit_pids
echo "CPU + Chart backend started"
echo "Terminal 1: python3 market_watch_terminal.py"
echo "Terminal 2: python3 options_straddle_terminal.py --index 1"
echo "Terminal 3: python3 execution_terminal.py"
echo "Safari    : http://127.0.0.1:8765"
