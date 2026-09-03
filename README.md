# Car Data Register 🚗

Samlar in svensk bilförsäljningsdata (scrape från Blocket), sparar i SQLite,
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
  (data-access), `scraper/` (respektfull Blocket-scrape), `ml/` (träning + värdering).
- **`app/streamlit_app.py`** — frontend. Läser DB endast via `repository`.
- **`scripts/`** — CLI för scrape och träning.

**Säkerhet:** all DB-åtkomst går genom `repository.py` med parametriserade
queries och en read-only-koppling för läsning. Input valideras med Pydantic.

## Kom igång

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Samla data (riktig scrape ELLER syntetisk för utveckling)
python scripts/run_scrape.py --query "" --pages 2
python scripts/run_scrape.py --synthetic 400     # om Blocket blockerar

# 2. Träna modellen
python scripts/run_train.py

# 3. Starta appen
streamlit run app/streamlit_app.py
```

## Tester

```bash
python -m pytest
```

## Not om scraping

Blocket kan blockera automatiserad hämtning (anti-bot). Scrapen respekterar
`robots.txt` och rate-limitar. Om den blockeras: utveckla mot `--synthetic`
(samma schema) och byt tillbaka. Selektorerna/fältmappningen i
`scraper/blocket.py` är det som behöver justeras när Blocket ändrar sin sajt.
