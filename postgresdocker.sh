docker run -d \
    --name postgres \
    -e POSTGRES_PASSWORD=password \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v /Users/mosborne/development/metamatch/postgresdata:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres