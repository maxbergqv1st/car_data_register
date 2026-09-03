# Car Data Register 🚗

Samlar in svensk bilförsäljningsdata (scrape från AutoUncle), sparar i SQLite,
och värderar en bil — både som **privatförsäljning** och **via handlare** — med
en scikit-learn-modell. Frontend i Streamlit.

## Arkitektur

```
scrape ──► CarListing (validering) ──► SQLite
                                          │  repository.py (read-only, parametriserat)
                                          ▼
                            ML-modell ◄── DataFrame
                                          │
                                          ▼
                                   Streamlit-app
```

- **`car_register/`** — kärnan: `models.py` (validering), `db.py` + `repository.py`
  (data-access), `scraper/` (respektfull AutoUncle-scrape), `ml/` (träning + värdering).
- **`app/streamlit_app.py`** — frontend. Läser DB endast via `repository`.
- **`scripts/`** — CLI för scrape och träning.

**Säkerhet:** all DB-åtkomst går genom `repository.py` med parametriserade
queries och en read-only-koppling för läsning. Input valideras med Pydantic.

## Kom igång

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Samla data (riktig scrape ELLER syntetisk för utveckling)
python scripts/run_scrape.py --pages 40          # ~1000 bilar (25/sida)
python scripts/run_scrape.py --synthetic 400     # om AutoUncle blockerar

# 2. Träna modellen
python scripts/run_train.py
python scripts/run_evaluate.py                   # jämför RF vs linjär baseline (MAE/MSE/RMSE + CV)

# 3. Starta appen
streamlit run app/streamlit_app.py
```

## Tester

```bash
python -m pytest
```

## Not om scraping

AutoUncle kan blockera automatiserad hämtning (anti-bot). Scrapen respekterar
`robots.txt` (hämtas med samma User-Agent som sidorna) och rate-limitar. Om den
blockeras: utveckla mot `--synthetic` (samma schema) och byt tillbaka.
Fältmappningen i `scraper/autouncle.py` (mil→km-faktor, bränsle-/växeltabeller)
är det som behöver justeras när AutoUncle ändrar sin ld+json.
