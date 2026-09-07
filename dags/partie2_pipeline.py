"""Orchestre le pipeline de données de la partie 2."""

from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator


with DAG(
    dag_id="partie2_pipeline",
    description="Extrait, transforme et charge les données des arrêts de tram.",
    start_date=datetime(2026, 9, 7),
    schedule=None,
    catchup=False,
) as dag:

    extract = DockerOperator(
        task_id="extract",
        image="sl-2026-dl-extract",
        container_name="airflow_extract",
        command="python src/partie2/extract.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="sl-2026-dl_default",
    )

    transform = DockerOperator(
        task_id="transform",
        image="sl-2026-dl-transform",
        container_name="airflow_transform",
        command="python src/partie2/transform.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="sl-2026-dl_default",
    )

    load = DockerOperator(
        task_id="load",
        image="sl-2026-dl-load",
        container_name="airflow_load",
        command="python src/partie2/load.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="sl-2026-dl_default",
    )

    extract >> transform >> load
