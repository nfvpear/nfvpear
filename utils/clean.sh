#!/bin/bash
sudo mn -c && sudo docker rm -f $(sudo docker ps -a | grep "mn" | awk '{ print $1}') 
