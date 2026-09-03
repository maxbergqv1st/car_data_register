"""CLI: läser DB -> tränar modell -> sparar model.joblib.

    python scripts/run_train.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import repository  # noqa: E402
from car_register.ml import train  # noqa: E402


def main() -> None:
    df = repository.load_dataframe()
    if len(df) < 20:
        print(
            f"För lite data ({len(df)} rader). Kör run_scrape.py först "
            "(ev. --synthetic 400).",
            file=sys.stderr,
        )
        sys.exit(1)
    metrics = train.train(df)
    print(
        f"Modell tränad på {metrics['n_train']} rader. "
        f"MAE={metrics['mae']:.0f} kr, R2={metrics['r2']:.3f}"
    )


if __name__ == "__main__":
    main()
