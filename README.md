# Car Data Register 🚗

Samlar in svensk begagnatbilsdata (scrape från **AutoUncle**), sparar i SQLite,
och värderar en bil — både som **privatförsäljning** och **via handlare** — med
en scikit-learn-modell. Svarar också på fråga *"är den här bilen ett fynd jämfört
med andra?"*. Frontend i Streamlit.

## Arkitektur

```
scrape (AutoUncle) ──► CarListing (Pydantic-validering) ──► SQLite
                                                              │  repository.py
                                                              │  (read-only, parametriserat)
                                                              ▼
                                              ML-modell  ◄──  DataFrame
                                          (RandomForest)      │
                                                              ▼
                                                       Streamlit-app
```

- **`car_register/`** — kärnan:
  - `models.py` — `CarListing`, trust boundary med Pydantic-validering. Definierar
    `FEATURE_COLUMNS` (indata) och `TARGET` (`price_sek`).
  - `db.py` + `repository.py` — data-access. Läsning via read-only-koppling.
  - `scraper/` — respektfull AutoUncle-scrape (`base.py` = HTTP + robots/rate-limit,
    `autouncle.py` = ld+json-parsning).
  - `ml/` — `features.py` (preprocessing), `train.py` (träning + utvärdering),
    `estimate.py` (värdering), `value.py` (fyndanalys).
- **`app/streamlit_app.py`** — frontend. Läser DB endast via `repository`.
- **`scripts/`** — CLI för scrape, träning och utvärdering.

**Säkerhet:** all DB-åtkomst går genom `repository.py` med parametriserade queries
och en read-only-koppling för läsning; kolumnnamn valideras mot en whitelist.
Input valideras med Pydantic innan den når DB eller modell.

## Kom igång

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Samla data (riktig scrape ELLER syntetisk för utveckling)
python scripts/run_scrape.py --pages 40          # ~1000 bilar (25/sida)
python scripts/run_scrape.py --synthetic 400     # om AutoUncle blockerar

# 2. Träna modellen och utvärdera
python scripts/run_train.py                      # tränar + sparar model.joblib
python scripts/run_evaluate.py                   # jämför RF vs linjär baseline

# 3. Starta appen
streamlit run app/streamlit_app.py
```

## Funktioner

### Värdering
Modellen tränas på handlarnas *utbudspriser*. Två avdrag ger ett realistiskt värde:

- **20 % värderingsavdrag** (`VALUATION_DISCOUNT`) — utbudspriser ligger högt, dras
  alltid av.
- **13 % privatmarginal** (`PRIVATE_MARGIN`) — en handlare tar påslag för
  garanti/marginal, så privatköp är billigare. Datan är ~100 % handlarannonser, så
  `seller_type`-featuren kan inte lära sig detta; marginalen dras därför av
  deterministiskt för privata rader. Båda är kalibreringsrattar i `ml/estimate.py`.

### Fyndanalys (`ml/value.py`)
- `deal()` — är begärt pris ett fynd mot modellens marknadsvärde? (fynd/marknadspris/dyr)
- `comparables()` — vad kostar liknande bilar (samma märke+modell) i datan?
- `rank_deals()` — de mest underprissatta annonserna, bästa fynd först.

I appen ligger "Bästa fynd" bakom en enkel lösenordsgrind (leksaksskydd, ej riktig
auth — datan är publik).

### Modellutvärdering (`ml/train.py` → `evaluate()`)
Jämför nuvarande **RandomForest** mot en **LinearRegression**-baseline på samma
indata, utan att röra produktionsträningen:

- **MAE/MSE/RMSE** på en 80/20 test-split.
- **5-fold korsvalidering** (MAE/RMSE, medel ± std) på hela datan — mer tillförlitligt
  än en enda split.

Kör `python scripts/run_evaluate.py` för en jämförelsetabell och sammanfattning.
På riktig data vinner RandomForest på alla tre måtten; på den nära-linjära
syntetiska datan vinner tvärtom LinearRegression.

## Tester

```bash
python -m pytest
```

Täcker DB-roundtrip + injection-skydd, scraper-parsning (fältmappning, mil→km,
säljartyp), värdering (avdrag + marginal) och modellutvärdering.

## Not om scraping

AutoUncle är en aggregator (drar in handlarannonser), så en källa räcker.
Listsidorna server-renderar 25 bilar/sida som schema.org JSON-LD → ingen
detaljsido-hämtning behövs. Scrapen respekterar `robots.txt` (hämtas med samma
User-Agent som sidorna) och rate-limitar mellan requests. Blockeras den: utveckla
mot `--synthetic` (samma schema). Fältmappningen i `scraper/autouncle.py`
(mil→km-faktor, bränsle-/växeltabeller, säljartyp-regex) är kalibreringsytan när
AutoUncle ändrar sin sajt.
