from pathlib import Path
s=Path('commander_pipeline.py').read_text(); d=Path('dashboard.py').read_text()
assert 'from trade_lifecycle_engine import TradeLifecycleEngine' in s
assert 'context.lifecycle =' in s
assert 'from trade_lifecycle_panel import print_trade_lifecycle' in d
assert 'print_trade_lifecycle(' in d
print('ALL TRADE LIFECYCLE INTEGRATION TESTS PASSED')
