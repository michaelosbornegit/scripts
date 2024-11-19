# Note, you must docker login to the registry first
docker build -t docker-registry.michaelosborne.dev/dev-container . 
docker push docker-registry.michaelosborne.dev/dev-container