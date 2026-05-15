from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"

# Databases available for analysis
DATABASES = {
    "chinook": f"sqlite:///{DB_DIR / 'chinook.db'}",
    "sakila": f"sqlite:///{DB_DIR / 'sakila.db'}",
    "northwind_small": f"sqlite:///{DB_DIR / 'northwind_small.sqlite'}"
}

# Which users have access to which databases
USER_DB_ACCESS = {
    "client1": ["chinook"],
    "client2": ["sakila"],
    "client3": ["northwind_small"],
    "admin": ["chinook", "sakila", "northwind_small"]
}
