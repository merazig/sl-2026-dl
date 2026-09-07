# Faire circuler des données entre des briques de stockage hétérogènes

Pipeline Data Engineering basé sur PostgreSQL, MinIO, DuckDB et MongoDB.

Le projet est réalisé en deux parties :

**Partie 1 :** dépôt et lecture d'un fichier Parquet dans MinIO.  
**Partie 2 :** extraction depuis PostgreSQL, transformation avec DuckDB et chargement dans MongoDB.
## Architecture
```
                         PARTIE 1

                     ┌─────────────┐
                     │    MinIO    │
                     │    raw      │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   Python    │
                     └─────────────┘

```
```
                         PARTIE 2

 PostgreSQL
     │
     ▼
 ┌─────────┐
 │ extract │
 └────┬────┘
      │
      ▼
 ┌──────────────────┐
 │ MinIO / raw      │
 │tram_stops.parquet│
 └────────┬─────────┘
          │
          ▼
 ┌───────────┐
 │ transform │
 │  DuckDB   │
 └─────┬─────┘
       │
       ▼
 ┌──────────────────────┐
 │ MinIO / curated      │
 │ tram_stops.parquet   │
 └──────────┬───────────┘
            │
            ▼
       ┌─────────┐
       │  load   │
       └────┬────┘
            │
            ▼
       ┌─────────┐
       │ MongoDB │
       └─────────┘
```
## Prérequis

Le projet nécessite :

- Docker
- Docker Compose
- Git

La base `PostgreSQL` utilisée pour l'extraction est déjà préparée et contient les données GTFS.

## Configuration

Les identifiants et informations de connexion ne sont pas stockés dans le code.

Créer un fichier `.env` à la racine du projet à partir de `.env.example`.

### Exemple :
```
DATABASE_URL=postgres://user:password@host:5432/dbname

MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

MONGO_URL=mongodb://mongo:27017
MONGO_DATABASE=transport
MONGO_COLLECTION=routes
```

Le fichier `.env` ne doit pas être versionné.

## Installation

Cloner le dépôt puis se placer dans le répertoire du projet :
```Bash
git clone https://github.com/merazig/sl-2026-dl.git
cd sl-2026-dl
```

Créer le fichier `.env` à partir de `.env.example` et renseigner les valeurs nécessaires.

## Partie 1

La partie 1 permet de déposer un fichier Parquet dans MinIO puis de le relire.

Le code se trouve dans :
```
src/
└── partie1/
    └── main.py
```

L'image Python est construite à partir du Dockerfile.

Pour construire l'image :
```bash
docker compose build partie1
```

Pour exécuter la partie 1 :
```bash
docker compose run --rm partie1
```

`MinIO` est utilisé comme stockage objet.

## Partie 2

La partie 2 met en place une architecture en zones raw et curated.

**1. Extraction**

Le fichier `extract.py` se connecte à `PostgreSQL` avec `SQLAlchemy` et `psycopg2`.

La requête récupère les informations nécessaires aux lignes de tram et à leurs arrêts.

Le résultat est enregistré au format Parquet puis déposé dans le bucket raw de MinIO.
```
PostgreSQL
    ↓
extract.py
    ↓
raw/tram_stops.parquet
```

Le fichier généré localement est placé dans :
```
export/tram_stops.parquet
```

Ce dossier est monté dans le conteneur par Docker Compose.

Pour exécuter l'extraction :
```bash
docker compose run --rm extract
```
**2. Transformation**

Le fichier `transform.py` récupère le Parquet depuis le bucket raw.

`DuckDB` est utilisé pour lire et transformer les données Parquet.

Les données sont nettoyées et enregistrées dans un nouveau fichier Parquet :
```
export/tram_stops_curated.parquet
```

Ce fichier est ensuite déposé dans le bucket curated.
```
raw/tram_stops.parquet
        ↓
     DuckDB
        ↓
curated/tram_stops.parquet
```

Pour exécuter la transformation :
```bash
docker compose run --rm transform
```
**3. Chargement**

Le fichier `load.py` récupère le Parquet depuis le bucket curated.

Les données sont regroupées par ligne de tram afin de produire des documents `MongoDB` contenant directement leurs arrêts.

Exemple :
```json
{
  "route_id": "IDFM:C01390",
  "route_short_name": "T3a",
  "route_type": 0,
  "stops": [
    {
      "stop_id": "IDFM:490920",
      "stop_name": "Porte de Vincennes",
      "stop_lat": 48.847,
      "stop_lon": 2.4103
    }
  ]
}
```

Pour exécuter le chargement :
```bash
docker compose run --rm load
```
### Exécution complète de la partie 2

Les services `extract`, `transform` et `load` utilisent la même image Python.

**Docker Compose** utilise `depends_on` et des conditions d'état pour respecter l'ordre d'exécution.

L'ordre attendu est :
```
extract
   ↓
transform
   ↓
load
```

Les services `MinIO` et `MongoDB` utilisent des healthcheck afin de vérifier leur disponibilité avant l'exécution des traitements qui en dépendent.

La partie 2 peut être lancée avec :
```bash
docker compose up --build extract transform load
````
```
Structure du projet
sl-2026-dl/
│
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
│
├── data/
│   └── tram_stops.parquet
│
├── export/
│   ├── tram_stops.parquet
│   └── tram_stops_curated.parquet
│
└── src/
    ├── __init__.py
    │
    ├── partie1/
    │   ├── __init__.py
    │   └── main.py
    │
    └── partie2/
        ├── __init__.py
        ├── extract.py
        ├── transform.py
        └── load.py
```
Les fichiers générés dans `export/` ne sont pas versionnés.

## Dépendances Python

Les principales bibliothèques utilisées sont :
```text
boto3==1.43.82
duckdb==1.5.5
pandas==3.0.5
psycopg2-binary==2.9.12
pyarrow==25.0.1
pymongo==4.17.0
SQLAlchemy==2.0.52
```
## Pourquoi faire transiter la donnée par le stockage objet ?

Le stockage objet permet de découpler les différentes étapes du pipeline.

Sans stockage intermédiaire, `PostgreSQL` devrait communiquer directement avec `MongoDB`. Les traitements seraient alors fortement couplés : une modification d'une étape pourrait avoir un impact direct sur les autres.

Avec `MinIO`, chaque étape travaille sur un fichier intermédiaire :
```
PostgreSQL → raw → transformation → curated → MongoDB
```

### Le stockage objet permet notamment :

- de conserver une copie de la donnée brute ;
- de rejouer une transformation sans interroger à nouveau PostgreSQL ;
- de découpler les étapes du pipeline ;
- de faciliter le contrôle et le débogage des données ;
- de permettre à plusieurs traitements de réutiliser les mêmes données.

## Pourquoi deux zones raw et curated ?

Les zones raw et curated ont des rôles différents.

### Zone raw

La zone raw contient les données extraites de la source avec un minimum de modifications.

Elle constitue une copie intermédiaire de la donnée source.

Dans ce projet :
```
raw/tram_stops.parquet
```
### Zone curated

La zone curated contient les données après transformation et nettoyage.

Elle est destinée à être consommée par les étapes suivantes du pipeline.

Dans ce projet :
```
curated/tram_stops.parquet
```

Séparer les deux zones permet de conserver la donnée brute et de distinguer clairement la donnée source de la donnée préparée.

Avec une seule zone, la donnée originale pourrait être écrasée par la donnée transformée. Il serait alors plus difficile de revenir à l'état initial ou de rejouer les transformations.

Cette séparation permet donc de mieux assurer la traçabilité, la reproductibilité et la maintenance du pipeline.

## Vérification

Après l'exécution du pipeline :

- 1. Le bucket `raw` doit contenir `tram_stops.parquet`.
- 2. Le bucket `curated` doit contenir `tram_stops.parquet`.
- 3. MongoDB doit contenir les documents regroupés par ligne.
