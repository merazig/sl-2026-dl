"""Charge les données curated dans MongoDB sous forme de documents par ligne."""

import os
from pathlib import Path

import boto3
import pandas as pd
from pymongo import MongoClient


CURATED_FILE = Path("export/tram_stops_curated.parquet")


def download_from_minio(file_path: Path) -> None:
    """Télécharge le fichier curated depuis MinIO."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    s3.download_file(
        "curated",
        "tram_stops.parquet",
        str(file_path),
    )


def create_documents(file_path: Path) -> list[dict]:
    """Transforme le Parquet en documents MongoDB regroupés par ligne."""
    dataframe = pd.read_parquet(file_path)

    documents = []

    for (route_id, route_short_name, route_type), group in dataframe.groupby(
        ["route_id", "route_short_name", "route_type"],
        dropna=False,
    ):
        stops = [
            {
                "stop_id": row.stop_id,
                "stop_name": row.stop_name,
                "stop_lat": row.latitude,
                "stop_lon": row.longitude,
            }
            for row in group.itertuples()
        ]

        documents.append(
            {
                "route_id": route_id,
                "route_short_name": route_short_name,
                "route_type": route_type,
                "stops": stops,
            }
        )

    return documents


def load_to_mongodb(documents: list[dict]) -> None:
    """Insère les documents dans MongoDB."""
    mongo_url = os.environ["MONGO_URL"]
    database_name = os.environ["MONGO_DATABASE"]
    collection_name = os.environ["MONGO_COLLECTION"]

    client = MongoClient(mongo_url)

    try:
        database = client[database_name]
        collection = database[collection_name]

        if documents:
            collection.delete_many({})
            collection.insert_many(documents)

        print(f"{len(documents)} lignes chargées dans MongoDB.")
    finally:
        client.close()


def main() -> None:
    """Exécute le chargement des données curated dans MongoDB."""
    CURATED_FILE.parent.mkdir(parents=True, exist_ok=True)

    download_from_minio(CURATED_FILE)

    documents = create_documents(CURATED_FILE)

    load_to_mongodb(documents)


if __name__ == "__main__":
    main()
