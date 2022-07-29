#!/bin/bash

docker pull dbeaver/cloudbeaver:latest
docker volume create cloudbeaverworkspace
docker run -d \
    --name cloudbeaver \
    -p 7766:8978 \
    -v cloudbeaverworkspace:/opt/cloudbeaver/workspace \
    dbeaver/cloudbeaver:latest