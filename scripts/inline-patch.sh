#!/bin/bash

content=$(cat)
echo "$content" > ~/dev/avalon/data/patch.p2c

./patch.sh
