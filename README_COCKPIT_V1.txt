COPY ALL FILES INTO YOUR CURRENT projectcommander FOLDER.

INSTALL + TEST:
python3 install_cockpit_v1.py
python3 -m py_compile commander_cpu.py market_watch_terminal.py options_straddle_terminal.py execution_terminal.py chart_server.py commander_state_store.py
python3 test_cockpit_v1.py

DAILY:
1. Fresh FYERS token/auth as usual.
2. ./start_commander_cockpit.sh
3. Open terminals:
   python3 market_watch_terminal.py
   python3 options_straddle_terminal.py --index 1
   python3 execution_terminal.py
4. Safari: http://127.0.0.1:8765

Options index: 1 NIFTY, 2 BANKNIFTY, 3 SENSEX.
Edit cockpit_config.py to change cash/index watchlists.
Stop backend: ./stop_commander_cockpit.sh
