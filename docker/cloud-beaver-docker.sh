#!/bin/bash

docker run --name cloudbeaver \
    -p 7766:8978 \
    -v cloudbeaverworkspace:/opt/cloudbeaver/workspace \
    dbeaver/cloudbeaver:latest