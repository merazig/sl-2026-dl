"""Transforme les données brutes des arrêts de tram avec DuckDB."""

import os
from pathlib import Path

import boto3
import duckdb
from botocore.exceptions import ClientError


RAW_FILE = Path("export/tram_stops.parquet")
CURATED_FILE = Path("export/tram_stops_curated.parquet")


def download_from_minio(file_path: Path) -> None:
    """Télécharge le fichier brut depuis le bucket raw de MinIO."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    s3.download_file(
        "raw",
        "tram_stops.parquet",
        str(file_path),
    )


def transform_data(input_path: Path, output_path: Path) -> None:
    """Nettoie les données brutes et produit le fichier curated."""
    input_file = str(input_path)
    output_file = str(output_path)

    with duckdb.connect() as connection:
        connection.execute(
            """
            COPY (
                SELECT DISTINCT
                    stop_id,
                    stop_name,
                    route_name,
                    latitude,
                    longitude
                FROM read_parquet(?)
                WHERE stop_id IS NOT NULL
                  AND stop_name IS NOT NULL
                  AND route_name IS NOT NULL
                  AND latitude BETWEEN -90 AND 90
                  AND longitude BETWEEN -180 AND 180
            )
            TO ?
            (FORMAT PARQUET);
            """,
            [input_file, output_file],
        )


def upload_to_minio(file_path: Path) -> None:
    """Dépose le fichier transformé dans le bucket curated de MinIO."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    bucket_name = "curated"

    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket_name)
        else:
            raise

    s3.upload_file(
        str(file_path),
        bucket_name,
        "tram_stops.parquet",
    )


def main() -> None:
    """Exécute la transformation des données brutes."""
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)

    download_from_minio(RAW_FILE)
    transform_data(RAW_FILE, CURATED_FILE)
    upload_to_minio(CURATED_FILE)

    print("Transformation terminée.")
    print("Fichier déposé dans le bucket curated.")


if __name__ == "__main__":
    main()
