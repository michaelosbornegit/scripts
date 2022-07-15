#!/bin/bash
mkdir -p ./7zipped

for FILE in *
do 
   echo ${FILE%%.*}
   if [[ $FILE != *.sh && $FILE != '7zipped' ]];
   then
      7z a -t7z ./7zipped/"${FILE%%.*}".7z "$FILE" -r
   fi
done || exit 1

EXITCODE=$?
test $EXITCODE -ne 0 && echo "Error! There is probably output above" || echo "Success!! Zipped files should be in the new directory"
exit $EXITCODE