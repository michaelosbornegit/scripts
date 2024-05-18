#!/bin/bash

if [ $# -eq 0 ]; then
  echo "Error: Please provide a container name (e.g., mike-dev)"
  exit 1
fi

container_name=$1

docker build -t $container_name .
# docker volume create $container_name
docker stop $container_name
docker rm $container_name
docker run \
  -it -d \
  --name=$container_name \
  -v '/var/run/docker.sock':'/var/run/docker.sock':'rw' \
  $container_name
  # -v $container_name:/home/mike \
docker exec $container_name sudo chmod 666 /var/run/docker.sock
docker exec -it $container_name /bin/zsh