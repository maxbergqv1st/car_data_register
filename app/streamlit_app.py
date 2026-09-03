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
from car_register.ml import estimate  # noqa: E402

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

tab_browse, tab_estimate = st.tabs(["📋 Bläddra annonser", "💰 Värdera bil"])

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
            }
            result = estimate.estimate(car)
            c1, c2 = st.columns(2)
            c1.metric("Privatförsäljning", f"{result['privat']:,} kr".replace(",", " "))
            c2.metric("Via handlare", f"{result['handlare']:,} kr".replace(",", " "))
