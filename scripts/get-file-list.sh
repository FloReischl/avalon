#!/bin/bash

cd ~/dev/avalo/scripts

echo "Paste file list (finish with an empty line / Enter):"

lines=()
while IFS= read -r line; do

# Bricht ab, wenn die eingegebene Zeile leer ist

[[ -z "$line" ]] && break
lines+=("$line")
done

# Verwandelt das Array in eine komma-separierte Liste

file_list=$(IFS=,; echo "${lines[*]}")

code2prompt ~/dev/avalo \
   --include="$file_list" \
   -F markdown \
   --output-file=~/dev/avalo/data/code2prompt-file-list.md


# #!/bin/bash

# cd ~/dev/avalo/scripts

# echo "Paste file list (complete with ENTER CTRL+d):"

# file_list=$(cat)

# file_list=$(echo "$file_list" | paste -sd, -)
# #echo $file_list

# code2prompt ~/dev/avalo \
#   --include="$file_list" \
#   -F markdown \
#   --output-file=./data/code2prompt-file-list.md
# #  --output-file=~/dev/avalo/scripts/data/code2prompt-file-list.md

