#!/bin/bash

docker run --gpus all -it \
    -v /mnt/c/Users/reson/Downloads:/workspace \
    --entrypoint bash \
    willprice/nvidia-ffmpeg