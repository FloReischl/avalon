#!/bin/bash

cd ~/dev/avalo/scripts

# read -p "Paste file list: " file_list
echo "Paste file list (complete with ENTER CTRL+d):"

file_list=$(cat)

file_list=$(echo "$file_list" | paste -sd, -)
#echo $file_list

code2prompt ~/dev/avalo \
  --include="$file_list" \
  -F markdown \
  --output-file=./data/code2prompt-file-list.md
#  --output-file=~/dev/avalo/scripts/data/code2prompt-file-list.md

