"""Entry point: run the pipeline and write the dataset to `data/v1/`.

    python -m cotizaciones_uy

Exit codes:
    0  a payload was written (possibly empty, if no providers are registered)
    1  providers were attempted and all failed; nothing was written
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from . import pipeline
from .registry import PROVIDERS
from .serialize import build_payload, dump_json

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "v1"


def main() -> int:
    now = datetime.now(UTC)
    result = pipeline.run(PROVIDERS, fetched_at=now)

    if not result.should_publish:
        print(
            f"All {result.attempted} provider(s) failed; leaving latest.json "
            f"untouched. Failures: {result.failures}",
            file=sys.stderr,
        )
        return 1

    payload = build_payload(result.rates, result.failures, generated_at=now)
    text = dump_json(payload)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "latest.json").write_text(text, encoding="utf-8")
    history_dir = DATA_DIR / "history"
    history_dir.mkdir(exist_ok=True)
    (history_dir / f"{now:%Y-%m-%d}.json").write_text(text, encoding="utf-8")

    print(
        f"Wrote {len(result.rates)} rate(s), {len(result.failures)} failure(s) "
        f"to {DATA_DIR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
