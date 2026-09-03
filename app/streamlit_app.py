"""Frontend: bläddra annonser och värdera en bil (privat vs handlare).

Läser ALDRIG DB direkt — går via car_register.repository (read-only, parametriserat).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from car_register import config, repository  # noqa: E402
from car_register.ml import estimate, value  # noqa: E402

st.set_page_config(page_title="Bilvärderaren", page_icon="🚗")
st.title("🚗 Bilvärderaren")

n = repository.count()
if n == 0:
    st.warning(
        "Databasen är tom. Kör `python scripts/run_scrape.py --synthetic 400` "
        "och `python scripts/run_train.py` först."
    )
    st.stop()
st.caption(f"{n} annonser i databasen.")

tab_browse, tab_estimate, tab_deals = st.tabs(
    ["📋 Bläddra annonser", "💰 Värdera bil", "🏆 Bästa fynd"]
)

with tab_browse:
    brands = ["(alla)"] + repository.distinct_values("brand")
    col1, col2 = st.columns(2)
    brand = col1.selectbox("Märke", brands)
    seller = col2.selectbox("Säljare", ["(alla)", "privat", "handlare"])
    rows = repository.fetch_listings(
        brand=None if brand == "(alla)" else brand,
        seller_type=None if seller == "(alla)" else seller,
    )
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tab_estimate:
    if not Path(config.MODEL_PATH).exists():
        st.warning("Ingen tränad modell. Kör `python scripts/run_train.py`.")
    else:
        with st.form("estimate"):
            c1, c2 = st.columns(2)
            brand = c1.selectbox("Märke", repository.distinct_values("brand"))
            model = c2.text_input("Modell", "V60")
            year = c1.number_input("Årsmodell", 1990, 2026, 2018)
            mileage = c2.number_input("Miltal (km)", 0, 1_000_000, 60_000, step=1000)
            hp = c1.number_input("Hästkrafter", 40, 1000, 150)
            fuel = c2.selectbox("Bränsle", repository.distinct_values("fuel"))
            gearbox = c1.selectbox("Växellåda", repository.distinct_values("gearbox"))
            seller = c2.selectbox("Säljare på annonsen", ["privat", "handlare"])
            asking = c1.number_input(
                "Begärt pris (kr)", 0, 5_000_000, 0, step=1000,
                help="Fyll i annonsens pris för att se om det är ett fynd.",
            )
            submitted = st.form_submit_button("Värdera")

        if submitted:
            car = {
                "brand": brand,
                "model": model,
                "model_year": int(year),
                "mileage_km": int(mileage),
                "horsepower": int(hp),
                "fuel": fuel,
                "gearbox": gearbox,
                "seller_type": seller,
            }
            result = estimate.estimate(car)
            c1, c2 = st.columns(2)
            c1.metric("Privatförsäljning", f"{result['privat']:,} kr".replace(",", " "))
            c2.metric("Via handlare", f"{result['handlare']:,} kr".replace(",", " "))
            if asking > 0:
                d = value.deal(car, int(asking))
                emoji = {"fynd": "🟢", "marknadspris": "🟡", "dyr": "🔴"}[d["verdict"]]
                side = "under" if d["pct_below_market"] >= 0 else "över"
                st.subheader(f"{emoji} {d['verdict'].capitalize()}")
                st.write(
                    f"Begärt {int(asking):,} kr mot marknadsvärde {d['predicted']:,} kr "
                    f"— {abs(d['pct_below_market']):.0%} {side} marknad.".replace(",", " ")
                )

            stats = value.comparables(repository.load_dataframe(), brand, model)
            if stats["n"]:
                st.caption(
                    f"{stats['n']} liknande {brand} {model} i datan: median "
                    f"{stats['median']:,} kr (spann {stats['min']:,}–{stats['max']:,} kr)."
                    .replace(",", " ")
                )

with tab_deals:
    st.subheader("🔒 Bästa fynd (premium)")
    # ponytail: leksaks-betalvägg, ett hårdkodat lösenord. INTE riktig säkerhet
    # (rankningen är publik bildata); byt till riktig auth om något känsligt låses.
    if st.text_input("Lösenord", type="password") != "money":
        st.warning("Lås upp med lösenord för att se de bästa fynden.")
    elif not Path(config.MODEL_PATH).exists():
        st.warning("Ingen tränad modell. Kör `python scripts/run_train.py`.")
    else:
        st.caption(
            "Annonser rankade efter hur långt under modellens marknadsvärde de "
            "ligger — störst fynd överst. (pct_below_market: 0.15 = 15 % under.)"
        )
        st.dataframe(
            value.rank_deals(repository.load_dataframe(), top=20),
            use_container_width=True,
        )
