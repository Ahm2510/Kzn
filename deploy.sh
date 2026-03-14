#!/bin/bash
set -e

echo "Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

echo "Stopping containers..."
docker-compose down

echo "Building and starting containers..."
docker-compose up --build -d

echo "Deployment finished!"
docker ps
