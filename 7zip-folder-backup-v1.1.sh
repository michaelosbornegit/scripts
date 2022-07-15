#!/bin/bash
if [ -z "$1" ]
  then
    echo "No argument supplied, please supply the folder you want to back up"
fi

if [ -d "$1" ]; then
   echo "'$1' found, creating backup of this folder ..."
else
   echo "Warning: '$1' NOT found, please supply a valid folder to zip"
   exit 1
fi

mkdir -p ./backups

name=$(basename $1)

7z a -t7z ./backups/$(date '+%Y-%m-%d')-"$name"-$(date '+%H%M%S').7z "$1" -r