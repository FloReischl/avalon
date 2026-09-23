#!/bin/bash

content=$(cat)
echo "$content" > ~/dev/avalo/data/patch.p2c

./patch.sh
