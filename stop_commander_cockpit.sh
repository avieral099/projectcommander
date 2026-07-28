#!/bin/zsh
cd "$(dirname "$0")"
[ -f .cockpit_pids ] && kill $(cat .cockpit_pids) 2>/dev/null || true
rm -f .cockpit_pids
echo "Cockpit backend stopped"
