# 🚗 Bilvärderaren

En prismodell för begagnade bilar, byggd som **en enda notebook** — cell för cell,
från dataset till färdig värdering. Ingen scraping, ingen databas, ingen app.

## Kör

```bash
pip install -r requirements.txt
jupyter notebook pipeline.ipynb
```

Kör cellerna uppifrån och ner.

## Pipeline (`pipeline.ipynb`)

| Steg | Vad |
|------|-----|
| 0 | Beroenden & konstanter (`EUR_SEK`, `PRIVATE_MARGIN`, `DEAL_THRESHOLD`) |
| 1 | Läs in `dataset/car_price_dataset.csv` (10 000 bilar) |
| 2 | Städa: dubletter, saknade värden, räkna om pris till SEK |
| 3 | Features & target (one-hot på kategoriska, numeriska rakt igenom) |
| 4 | Träna RandomForest + MAE/R² på 80/20-split |
| 5 | Jämför RandomForest vs LinearRegression (MAE/MSE/RMSE + 5-fold CV), vinnaren blir modellen |
| 6 | Feature importance |
| 7 | **Output:** värdering privat vs handlare |
| 8 | **Output:** fyndanalys (`deal`, `comparables`, `rank_deals`) |

## Antaganden (kalibreringsrattar, cell 0)

- **`EUR_SEK = 11.5`** — datasetets `Price` saknar valuta; vi antar EUR och räknar om till SEK.
- **`PRIVATE_MARGIN = 0.13`** — datasetet saknar säljartyp, så gapet privat/handlare
  sätts deterministiskt istället för att läras från data.
- **`DEAL_THRESHOLD = 0.10`** — ≥10 % under marknadsvärde = fynd, ≥10 % över = dyr.

På den här datan vinner **LinearRegression** (priset är nästan linjärt i årsmodell/miltal/motorstorlek).
