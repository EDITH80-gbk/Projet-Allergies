"""
Stockage des données sur les allergies vers la base SQLite
Gestion des erreurs, logs, vérifications
"""

import sys
import logging
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# CLEAN files
allergies_clean_filepath = "../data/allergies_clean.csv"
allergies_clean_categories_filepath = "../data/allergies_clean_categories.csv"

# Database file path
db_filepath = "../data/allergen_chip_challenge.db"

# ---------------------------------------------------------------------------
# Logging - chaque execution crée un nouveau fichier de log
# ---------------------------------------------------------------------------

log_file = f"../data/store_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stockage de la table allergies
# ---------------------------------------------------------------------------

def store_data_allergies(source: Path, conn):

    logger.info(f"Stockage en base : {source.name}")
    df = pd.read_csv(filepath_or_buffer=source)

   # Save dataframe as SQL table
    df.to_sql(
        name="allergies",      # table name
        con=conn,
        if_exists="replace",  # options: fail, replace, append
        index=False
    )

# ---------------------------------------------------------------------------
# Stockage de la table allergies par catégories
# ---------------------------------------------------------------------------

def store_data_allergies_categories(source: Path, conn):

    logger.info(f"Stockage en base : {source.name}")
    df = pd.read_csv(filepath_or_buffer=source)

   # Save dataframe as SQL table
    df.to_sql(
        name="allergies_categories",      # table name
        con=conn,
        if_exists="replace",  # options: fail, replace, append
        index=False
    )

# ---------------------------------------------------------------------------
# Stockage de toutes les tables, vers la base SQLite
# ---------------------------------------------------------------------------

def store_all():
    logger.info("Stockage SQLite")
    # Se connecter, ou créer si elle n'existe pas
    conn = sqlite3.connect(database=db_filepath)

    try:
        # Ici, on appelle une procédure pour chaque table à stocker :
        store_data_allergies(Path(allergies_clean_filepath), conn)
        store_data_allergies_categories(Path(allergies_clean_categories_filepath), conn)
    except Exception as e:
        logger.error(f"Erreur : {e}")
    finally:
        # Fermer enfin la connexion à la base
        conn.close()

    logger.info("Stockage terminé")

if __name__ == "__main__":
    store_all()

