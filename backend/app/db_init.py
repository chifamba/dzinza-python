# backend/app/db_init.py
import logging
from sqlalchemy.orm import Session


def populate_database(db: Session):
    """Populates the database with initial data if it's empty."""
    logging.info("TODO: Populate the database with initial data.")


def create_tables(engine):
    """Creates all tables in the database."""
    logging.info("TODO: Create all tables in the database.")
