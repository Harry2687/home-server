#!/bin/bash

cd /home/harryzhong/docker

docker compose pull

docker compose up -d --remove-orphans

docker system prune -af
