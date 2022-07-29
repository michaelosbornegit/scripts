#!/bin/bash

docker run -d \
    --name postgres \
    -e POSTGRES_PASSWORD=password \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v postgres:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres:latest