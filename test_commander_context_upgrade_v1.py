from __future__ import annotations

import tempfile
from pathlib import Path

from premium_intelligence_1m import PremiumIntelligence1M


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"

        with PremiumIntelligence1M(db_path) as database:
            columns = {
                row["name"]
                for row in database.connection.execute(
                    "PRAGMA table_info(intelligence_summaries)"
                ).fetchall()
            }

            required = {
                "vwap_state",
                "ema_structure",
                "supertrend_state",
                "battle_status",
                "battle_score",
                "evidence_verdict",
                "call_confidence",
                "put_confidence",
                "engine_agreement",
            }

            missing = required - columns
            assert not missing, f"Missing columns: {sorted(missing)}"

    print("ALL COMMANDER CONTEXT UPGRADE V1 TESTS PASSED")


if __name__ == "__main__":
    main()
