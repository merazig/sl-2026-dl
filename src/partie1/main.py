"""Test de connexion à MinIO et MongoDB pour la partie 1."""

import os
import logging

import boto3
from botocore.exceptions import ClientError
from pymongo import MongoClient


def main():
    """Exécute les tests de connexion à MinIO et MongoDB."""
    # =========================
    # MinIO
    # =========================

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    bucket_name = "raw"
    file_path = "data/tram_stops.parquet"
    object_name = "tram_stops.parquet"

    logger = logging.getLogger(__name__)
    
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info(f"Le bucket '{bucket_name}' existe déjà.")
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        logger.info(f"Le bucket '{bucket_name}' a été créé.")

    s3.upload_file(file_path, bucket_name, object_name)
    logger.info("Fichier déposé dans MinIO.")

    s3.download_file(
        bucket_name,
        object_name,
        "data/tram_stops_downloaded.parquet",
    )
    logger.info("Fichier relu depuis MinIO.")

    # =========================
    # MongoDB
    # =========================

    mongo_client = MongoClient(os.environ["MONGO_URI"])

    try:
        database = mongo_client["transport"]
        collection = database["routes"]

        documents = [
            {
                "route_name": "T3a",
                "stops": [
                    {
                        "stop_id": "IDFM:490920",
                        "stop_name": "Porte de Vincennes",
                        "latitude": 48.8470,
                        "longitude": 2.4103,
                    },
                    {
                        "stop_id": "IDFM:463154",
                        "stop_name": "Montempoivre",
                        "latitude": 48.8419,
                        "longitude": 2.4048,
                    },
                ],
            },
            {
                "route_name": "T3b",
                "stops": [
                    {
                        "stop_id": "IDFM:123456",
                        "stop_name": "Porte de Pantin",
                        "latitude": 48.8880,
                        "longitude": 2.3930,
                    },
                ],
            },
        ]

        collection.insert_many(documents)
        logger.info("Documents ajoutés dans MongoDB.")

        route = collection.find_one({"route_name": "T3a"})
        logger.info("Route trouvée :", route)

        pipeline = [
            {
                "$project": {
                    "route_name": 1,
                    "number_of_stops": {"$size": "$stops"},
                }
            }
        ]

        results = collection.aggregate(pipeline)

        for result in results:
            logger.info(result)
    finally:
        mongo_client.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    main()
