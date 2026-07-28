import sys
import types


dashboard = types.ModuleType(
    "dashboard"
)
dashboard.main = lambda: None
sys.modules["dashboard"] = dashboard


import commander_live_runner


assert (
    commander_live_runner.REFRESH_SECONDS
    == 60
)
assert (
    commander_live_runner.RETRY_SECONDS
    == 20
)
assert (
    commander_live_runner.run_dashboard_snapshot()
    is True
)

print(
    "ALL COMMANDER LIVE RUNNER V1 "
    "TESTS PASSED"
)
