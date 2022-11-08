
#!/bin/bash

docker pull mongo-express:latest
docker stop mongo-express
docker rm mongo-express
docker run -d \
    --name mongo-express \
    -e ME_CONFIG_MONGODB_SERVER="host.docker.internal" \
    -e ME_CONFIG_MONGODB_ADMINUSERNAME=test \
    -e ME_CONFIG_MONGODB_ADMINPASSWORD=test \
    -p 9901:8081 \
    mongo-express:latest