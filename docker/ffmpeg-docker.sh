#!/bin/bash

docker run -d --gpus all -it \
    -v "/mnt/z/My Videos":/workspace \
    --entrypoint bash \
    willprice/nvidia-ffmpeg:latest