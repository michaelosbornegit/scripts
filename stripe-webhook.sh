#!/bin/bash

stripe listen --forward-to localhost:8080/payments/stripehook
