from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()


def get_db():

    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")

    try:
        client = MongoClient(uri)
        db = client[db_name]
        print("Conectado a la base de datos")
        return db
    except Exception as e:
        print(f"1. Error al conectar a la base de datos: {e}")
        return None