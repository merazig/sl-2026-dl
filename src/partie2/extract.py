"""Extrait les données des arrêts de tram depuis PostgreSQL vers MinIO."""

import os
from pathlib import Path

import boto3
import pandas as pd
from sqlalchemy import create_engine, text


def get_arrets_tram(database_url: str) -> pd.DataFrame:
    """Retourne les arrêts de tram avec leur ligne et leurs coordonnées."""
    query = """
        SELECT DISTINCT
            r.route_id,
            r.route_short_name,
            r.route_type,
            s.stop_id,
            s.stop_name,
            s.stop_lat AS latitude,
            s.stop_lon AS longitude
        FROM stops s
        JOIN stop_times st
            ON s.stop_id = st.stop_id
        JOIN trips t
            ON st.trip_id = t.trip_id
        JOIN routes r
            ON t.route_id = r.route_id
        WHERE r.route_short_name LIKE 'T%'
        ORDER BY r.route_short_name, s.stop_name;
    """

    engine = create_engine(
        database_url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1,
        )
    )

    try:
        with engine.connect() as connection:
            return pd.read_sql(text(query), connection)

    finally:
        engine.dispose()


def upload_to_minio(file_path: Path) -> None:
    """Dépose le fichier Parquet dans le bucket raw de MinIO."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    bucket_name = "raw"
    object_name = "tram_stops.parquet"

    try:
        s3.head_bucket(Bucket=bucket_name)
    except Exception:
        s3.create_bucket(Bucket=bucket_name)

    s3.upload_file(str(file_path), bucket_name, object_name)

    print(f"{object_name} déposé dans le bucket {bucket_name}.")


def main() -> None:
    """Exécute l'extraction PostgreSQL et le dépôt dans MinIO."""
    database_url = os.environ["DATABASE_URL"]

    output_path = Path("export/tram_stops.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = get_arrets_tram(database_url)
    dataframe.to_parquet(output_path, index=False)

    print(f"{len(dataframe)} lignes extraites depuis PostgreSQL.")

    upload_to_minio(output_path)


if __name__ == "__main__":
    main()
