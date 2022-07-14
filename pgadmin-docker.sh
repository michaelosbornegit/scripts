docker run -d \
    --name pgadmin4 \
    -e PGADMIN_DEFAULT_EMAIL=test@test.com \
    -e PGADMIN_DEFAULT_PASSWORD=password \
    -v /Users/mosborne/development/metamatch/pgadmindata:/var/lib/pgadmin \
    -p 7654:80 \
    dpage/pgadmin4