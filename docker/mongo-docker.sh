#!/bin/bash

docker pull mongo:latest
docker volume create mongo
docker stop mongo
docker rm mongo
docker run -d \
    --name mongo \
    -e MONGO_INITDB_ROOT_PASSWORD=test \
    -e MONGO_INITDB_ROOT_USERNAME=test \
    -v mongo:/data/db \
    -p 27017:27017 \
    mongo:latest