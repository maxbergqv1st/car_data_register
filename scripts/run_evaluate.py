"""CLI: jämför värderingsmodeller (RandomForest vs LinearRegression-baseline).

    python scripts/run_evaluate.py

Utvärderar bara och skriver ut en jämförelsetabell — sparar ingen modell.
Kör run_train.py för att träna/spara produktionsmodellen.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import repository  # noqa: E402
from car_register.ml import train  # noqa: E402

# Tröskel för när korsvalideringens spridning räknas som "hög" (std relativt medel).
_HIGH_SPREAD = 0.15


def _kr(x: float) -> str:
    """Heltal med mellanslag som tusentalsavgränsare."""
    return f"{x:,.0f}".replace(",", " ")


def main() -> None:
    df = repository.load_dataframe()
    if len(df) < 20:
        print(f"För lite data ({len(df)} rader). Kör run_scrape.py först.", file=sys.stderr)
        sys.exit(1)

    res = train.evaluate(df)

    # --- Jämförelsetabell: test-split bredvid korsvalidering ---
    print(f"\nUtvärdering på {len(df)} bilar — 80/20 test-split + 5-fold korsvalidering\n")
    head = f"{'Modell':<30}{'MAE':>11}{'MSE':>18}{'RMSE':>11}   {'CV-MAE (medel ± std)':>24}"
    print(head)
    print("-" * len(head))
    for name, m in res.items():
        cv = f"{_kr(m['cv_mae_mean'])} ± {_kr(m['cv_mae_std'])}"
        print(f"{name:<30}{_kr(m['mae']):>11}{_kr(m['mse']):>18}{_kr(m['rmse']):>11}   {cv:>24}")

    # Måtten kort:
    print(
        "\nMAE = snittfel i kr (lätt att tolka) · MSE = kvadrerat fel (straffar stora "
        "avvikelser) · RMSE = √MSE i kr (extremvärdeskänsligt)."
    )

    # --- STEG 3: sammanfattning ---
    print("\n--- Sammanfattning ---")
    winners = {mått: min(res, key=lambda n: res[n][mått]) for mått in ("mae", "mse", "rmse")}
    if len(set(winners.values())) == 1:
        best = next(iter(winners.values()))
        print(f"Bäst på alla tre felmåtten (MAE/MSE/RMSE): {best}.")
    else:
        best = winners["mae"]
        print(f"Lägst MAE: {winners['mae']} · lägst MSE: {winners['mse']} · lägst RMSE: {winners['rmse']}.")

    # Korsvalideringens spridning: hög std relativt medel = datan för liten/ojämn.
    for name, m in res.items():
        spread = m["cv_mae_std"] / m["cv_mae_mean"] if m["cv_mae_mean"] else 0
        flagga = "HÖG spridning" if spread > _HIGH_SPREAD else "stabil"
        print(f"  {name}: CV-MAE {_kr(m['cv_mae_mean'])} ± {_kr(m['cv_mae_std'])} ({spread:.0%}, {flagga}).")
    if any(m["cv_mae_std"] / m["cv_mae_mean"] > _HIGH_SPREAD for m in res.values() if m["cv_mae_mean"]):
        print("  Hög spridning mellan folden tyder på att datan är för liten eller ojämn.")

    if best.startswith("RandomForest"):
        print(
            "Trolig orsak: LinearRegression antar räta samband och missar icke-linjära\n"
            "mönster som värdeminskning över tid (värdet faller snabbare de första åren)\n"
            "och interaktioner mellan märke/modell och miltal — sånt fångar RandomForest."
        )


if __name__ == "__main__":
    main()
