#!/bin/bash

(
  snapraid sync
) 2>&1 | tee -a /home/harryzhong/docker/logs/$(date +%F_%H-%M-%S)_snapraid_sync.log
