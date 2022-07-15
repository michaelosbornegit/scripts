#!/bin/bash

docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=CLIAdmin1" \
   -v sqlvolume:/var/opt/mssql \
   -p 1433:1433 --name mssql --hostname sql1 \
   -d mcr.microsoft.com/mssql/server:2019-latest