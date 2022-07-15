#!/bin/bash

docker run --gpus all -it \
    -v "/mnt/z/My Videos":/workspace \
    --entrypoint bash \
    willprice/nvidia-ffmpeg