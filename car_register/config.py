"""Central konfiguration. Sökvägar och scrape-inställningar på ett ställe."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "cars.db"
MODEL_PATH = ROOT / "model.joblib"

# Respektfull scraping: en realistisk User-Agent och en tydlig fördröjning
# mellan requests så vi inte belastar sajten.
USER_AGENT = (
    "car-data-register/0.1 (skolprojekt; kontakt: mjmaxbq@icloud.com)"
)
REQUEST_DELAY_SECONDS = 2.5
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3

# AutoUncle begagnat-lista. Paginering med `page` (filtrerad sök är robots-blockad).
AUTOUNCLE_SEARCH_URL = "https://www.autouncle.se/se/begagnade-bilar"
