docker run --name cloudbeaver --rm -ti \
    -p 7766:8978 \
    -v /Users/mosborne/development/metamatch/cloudbeaverworkspace:/opt/cloudbeaver/workspace \
    dbeaver/cloudbeaver:latest