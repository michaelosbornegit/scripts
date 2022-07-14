#!/bin/bash

# remove trailing slash if it exists
trimmedFile=${1%/}
mkdir $trimmedFile/h264

for file in $trimmedFile/*
do
    # only convert mp4
    if [[ ( $file == *.mp4 ) || ( $file == *.MP4 ) ]]
    then
        fileName=${file##*/}
        echo "$file: `ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -i "$file" -c:v h264_nvenc -preset slow -cq:v 1 "$trimmedFile/h264/$fileName"`"
    fi
done

echo "Success"