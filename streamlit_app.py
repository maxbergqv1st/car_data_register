"""Bilvärderaren — Streamlit-frontend till pipelinen i pipeline.ipynb.

Samma logik som notebooken: läs dataset, träna vinnaren (RF vs LinReg), och
servera värdering + fyndanalys. Modellen tränas en gång och cachas.

    streamlit run streamlit_app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CSV = "dataset/car_price_dataset.csv"
EUR_SEK = 11.5            # datasetets Price saknar valuta -> anta EUR, räkna om till SEK
PRIVATE_MARGIN = 0.13     # handlare tar påslag -> privatköp billigare (datan saknar säljartyp)
DEAL_THRESHOLD = 0.10     # >=10 % under marknad = fynd, >=10 % över = dyr

CAT = ["Brand", "Model", "Fuel_Type", "Transmission"]
NUM = ["Year", "Engine_Size", "Mileage", "Doors", "Owner_Count"]
TARGET = "price_sek"


def _pipe(model):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
        ("num", "passthrough", NUM),
    ])
    return Pipeline([("prep", prep), ("model", model)])


def _new(name):
    return (RandomForestRegressor(n_estimators=200, random_state=42)
            if name == "RandomForest" else LinearRegression())


@st.cache_resource(show_spinner="Tränar modellen…")
def build():
    """Läs data, jämför modeller, refit:a vinnaren på all data. Cachas mellan körningar."""
    df = pd.read_csv(CSV, sep=";").drop_duplicates().reset_index(drop=True)
    df[TARGET] = (df["Price"] * EUR_SEK).round().astype(int)
    X, y = df[CAT + NUM], df[TARGET]

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    rows = {}
    for name in ("RandomForest", "LinearRegression"):
        pipe = _pipe(_new(name)).fit(X_tr, y_tr)
        p = pipe.predict(X_te)
        mse = mean_squared_error(y_te, p)
        cv = -cross_val_score(_pipe(_new(name)), X, y, cv=5,
                              scoring="neg_mean_absolute_error")
        rows[name] = {"MAE": mean_absolute_error(y_te, p), "RMSE": mse ** 0.5,
                      "CV-MAE": cv.mean(), "CV-std": cv.std()}
    comparison = pd.DataFrame(rows).T
    winner = comparison["CV-MAE"].idxmin()
    model = _pipe(_new(winner)).fit(X, y)

    # Feature importance via RandomForest, summerad tillbaka till ursprungskolumn.
    imp_rf = _pipe(RandomForestRegressor(n_estimators=200, random_state=42)).fit(X, y)
    names = imp_rf.named_steps["prep"].get_feature_names_out()
    imp = pd.Series(imp_rf.named_steps["model"].feature_importances_, index=names)

    def orig(n):
        body = n.split("__", 1)[1]
        return next((c for c in CAT + NUM if body == c or body.startswith(c + "_")), body)

    importance = imp.groupby([orig(n) for n in names]).sum().sort_values(ascending=False)
    return df, model, winner, comparison, importance


def kr(x) -> str:
    return f"{int(round(x)):,} kr".replace(",", " ")


df, model, winner, comparison, importance = build()


def estimate(car: dict) -> dict:
    base = model.predict(pd.DataFrame([car])[CAT + NUM])[0]
    return {"privat": base * (1 - PRIVATE_MARGIN), "handlare": base}


def deal(car: dict, asking: int) -> dict:
    predicted = model.predict(pd.DataFrame([car])[CAT + NUM])[0]
    pct = (predicted - asking) / predicted
    verdict = ("fynd" if pct >= DEAL_THRESHOLD
               else "dyr" if pct <= -DEAL_THRESHOLD else "marknadspris")
    return {"predicted": predicted, "pct": pct, "verdict": verdict}


# ---------------------------------------------------------------- UI
st.set_page_config(page_title="Bilvärderaren", page_icon="🚗", layout="wide")
st.markdown(
    "<h1 style='margin-bottom:0'>🚗 Bilvärderaren</h1>"
    f"<p style='color:gray;margin-top:4px'>{len(df):,} bilar · modell: <b>{winner}</b> · "
    f"snittfel ±{kr(comparison.loc[winner, 'CV-MAE'])}</p>".replace(",", " "),
    unsafe_allow_html=True,
)

tab_value, tab_deals, tab_model = st.tabs(["💰 Värdera bil", "🏆 Bästa fynd", "📊 Modell"])

with tab_value:
    with st.form("car"):
        c1, c2, c3 = st.columns(3)
        brand = c1.selectbox("Märke", sorted(df["Brand"].unique()))
        models = sorted(df[df["Brand"] == brand]["Model"].unique())
        car_model = c2.selectbox("Modell", models)
        year = c3.slider("Årsmodell", int(df["Year"].min()), int(df["Year"].max()), 2019)
        fuel = c1.selectbox("Bränsle", sorted(df["Fuel_Type"].unique()))
        transmission = c2.selectbox("Växellåda", sorted(df["Transmission"].unique()))
        engine = c3.slider("Motorstorlek (l)", 1.0, 5.0, 2.0, step=0.1)
        mileage = c1.number_input("Miltal (km)", 0, 500_000, 60_000, step=5_000)
        doors = c2.selectbox("Dörrar", [2, 3, 4, 5], index=2)
        owners = c3.selectbox("Antal ägare", [1, 2, 3, 4, 5])
        asking = c1.number_input("Begärt pris (kr, valfritt)", 0, 5_000_000, 0, step=10_000,
                                 help="Fyll i annonspriset för att se om det är ett fynd.")
        submitted = st.form_submit_button("Värdera", type="primary", use_container_width=True)

    if submitted:
        car = {"Brand": brand, "Model": car_model, "Year": year, "Engine_Size": engine,
               "Fuel_Type": fuel, "Transmission": transmission, "Mileage": mileage,
               "Doors": doors, "Owner_Count": owners}
        est = estimate(car)
        c1, c2 = st.columns(2)
        c1.metric("👤 Privatförsäljning", kr(est["privat"]))
        c2.metric("🏢 Via handlare", kr(est["handlare"]))

        if asking > 0:
            d = deal(car, int(asking))
            color = {"fynd": "green", "marknadspris": "orange", "dyr": "red"}[d["verdict"]]
            emoji = {"fynd": "🟢", "marknadspris": "🟡", "dyr": "🔴"}[d["verdict"]]
            side = "under" if d["pct"] >= 0 else "över"
            st.markdown(
                f"### {emoji} :{color}[{d['verdict'].capitalize()}]  \n"
                f"Begärt **{kr(asking)}** mot marknadsvärde **{kr(d['predicted'])}** — "
                f"**{abs(d['pct']):.0%} {side}** marknad."
            )

        same = df[(df["Brand"] == brand) & (df["Model"] == car_model)]["price_sek"]
        if not same.empty:
            st.caption(
                f"{same.size} liknande {brand} {car_model} i datan · median "
                f"{kr(same.median())} (spann {kr(same.min())}–{kr(same.max())})."
            )

with tab_deals:
    st.subheader("Mest underprissatta bilar i datan")
    st.caption("Rankade efter hur långt under modellens marknadsvärde de ligger. "
               "OBS: in-sample-prediktion — relativa fynd, inte exakta.")
    top = st.slider("Antal", 5, 50, 15)
    ranked = df.copy()
    ranked["market_price"] = model.predict(df[CAT + NUM])
    ranked["under_market"] = ((ranked["market_price"] - ranked["price_sek"])
                              / ranked["market_price"])
    view = (ranked.sort_values("under_market", ascending=False)
            .head(top)[["Brand", "Model", "Year", "Mileage", "price_sek",
                        "market_price", "under_market"]])
    st.dataframe(
        view, use_container_width=True, hide_index=True,
        column_config={
            "Mileage": st.column_config.NumberColumn("Miltal", format="%d km"),
            "price_sek": st.column_config.NumberColumn("Begärt", format="%d kr"),
            "market_price": st.column_config.NumberColumn("Marknad", format="%d kr"),
            "under_market": st.column_config.ProgressColumn(
                "Under marknad", format="percent", min_value=0.0, max_value=0.3),
        },
    )

with tab_model:
    st.subheader("Modelljämförelse")
    st.caption("RandomForest vs LinearRegression — MAE/RMSE (test-split) och 5-fold CV-MAE. "
               f"Vinnaren (lägst CV-MAE) är **{winner}**.")
    st.dataframe(comparison.style.format("{:,.0f}").highlight_min(
        subset=["CV-MAE"], color="#1b5e20"), use_container_width=True)
    st.subheader("Feature importance")
    st.caption("Vilka egenskaper driver priset mest (RandomForest).")
    st.bar_chart(importance, horizontal=True)
