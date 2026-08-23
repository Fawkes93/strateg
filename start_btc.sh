#!/bin/zsh
cd /Users/carauslivian/strateg
mkdir -p results
nohup /usr/bin/caffeinate -dims /Users/carauslivian/reaktor/.venv/bin/python3 -u run_fade_btc.py >> results/fade_btc.log 2>&1 &
echo "PID $!"
sleep 2
tail -20 results/fade_btc.log
