#!/bin/bash

docker run --rm -it stripe/stripe-cli:latest \
    listen --forward-to localhost:8080/payments/stripehook \
    --api-key API_KEY_HERE
