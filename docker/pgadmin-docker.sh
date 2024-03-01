#!/bin/bash

docker pull dpage/pgadmin4:latest
docker volume create pgadmin
docker stop pgadmin
docker rm pgadmin

docker run -d \
    --name pgadmin4 \
    -e PGADMIN_DEFAULT_EMAIL=test@test.com \
    -e PGADMIN_DEFAULT_PASSWORD=password \
    -v pgadmin:/var/lib/pgadmin \
    -p 7654:80 \
    dpage/pgadmin4:latest