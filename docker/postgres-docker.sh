#!/bin/bash

docker pull postgres:latest
docker volume create postgres
docker stop postgres
docker rm postgres

docker run -d \
    --name postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v postgres:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres:latest