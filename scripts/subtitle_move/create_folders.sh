#!/bin/bash
SUBS_DIR="/Users/changikchoi/Desktop/Suits Subs/Suits - season 1.en/Subs"

for i in $(seq -w 1 12); do
    folder_name="Suits.S01E${i}.720p.HDTV.x264"
    mkdir -p "$SUBS_DIR/$folder_name"
    echo "Created: $folder_name"
done

echo "Done! Listing Subs directory:"
ls -la "$SUBS_DIR"
