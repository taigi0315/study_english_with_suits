#!/bin/bash

# Generic Subtitle Organizer
# Usage: Run this script inside any "Suits - season X.en" folder.
# It will:
# 1. Detect .srt files
# 2. Extract Season (S) and Episode (E) numbers (e.g., from "2x05")
# 3. Create the folder structure: ./Subs/Suits.S02E05.720p.HDTV.x264/
# 4. Copy the .srt file to that folder as "English.srt"

mkdir -p Subs

echo "Scanning for .srt files..."

# Loop through all .srt files in the current directory
find . -maxdepth 1 -name "*.srt" | while read -r file; do
    filename=$(basename "$file")
    
    # Try to match patterns like "1x01", "2x14", "S01E01"
    # We use sed to extract numbers. 
    # This regex looks for a number, followed by 'x' or 'E', followed by another number.
    
    if [[ $filename =~ ([0-9]+)x([0-9]+) ]]; then
        season=${BASH_REMATCH[1]}
        episode=${BASH_REMATCH[2]}
    elif [[ $filename =~ S([0-9]+)E([0-9]+) ]]; then
        season=${BASH_REMATCH[1]}
        episode=${BASH_REMATCH[2]}
    else
        echo "⚠️  Could not detect episode info for: $filename"
        continue
    fi

    # Pad numbers with leading zeros if needed (e.g., 1 -> 01)
    season_padded=$(printf "%02d" $season)
    episode_padded=$(printf "%02d" $episode)

    # Construct new folder name
    target_folder="Subs/Suits.S${season_padded}E${episode_padded}.720p.HDTV.x264"
    
    # Create directory
    mkdir -p "$target_folder"

    # Copy and rename file
    cp "$file" "$target_folder/English.srt"
    
    echo "✓ Processed: $filename -> $target_folder/English.srt"
done

echo ""
echo "Organization complete!"
