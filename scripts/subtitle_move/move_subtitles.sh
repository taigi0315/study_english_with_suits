#!/bin/bash
# Run this script from: /Users/changikchoi/Desktop/Suits Subs/Suits - season 1.en
# Usage: bash move_subtitles.sh

BASE_DIR="$(pwd)"
SUBS_DIR="$BASE_DIR/Subs"

echo "Moving subtitle files to episode folders..."

cp "$BASE_DIR/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt" "$SUBS_DIR/Suits.S01E01.720p.HDTV.x264/English.srt" && echo "✓ E01"
cp "$BASE_DIR/Suits - 1x02 - Errors and Omissions.HDTV.FQM.en.srt" "$SUBS_DIR/Suits.S01E02.720p.HDTV.x264/English.srt" && echo "✓ E02"
cp "$BASE_DIR/Suits - 1x03 - Inside Track.HDTV.CTU.en.srt" "$SUBS_DIR/Suits.S01E03.720p.HDTV.x264/English.srt" && echo "✓ E03"
cp "$BASE_DIR/Suits - 1x04 - Dirty Little Secrets.720p HDTV.DIMENSION.en.srt" "$SUBS_DIR/Suits.S01E04.720p.HDTV.x264/English.srt" && echo "✓ E04"
cp "$BASE_DIR/Suits - 1x05 - Bail Out.en.srt" "$SUBS_DIR/Suits.S01E05.720p.HDTV.x264/English.srt" && echo "✓ E05"
cp "$BASE_DIR/Suits - 1x06 - Tricks of the Trade.HDTV.en.srt" "$SUBS_DIR/Suits.S01E06.720p.HDTV.x264/English.srt" && echo "✓ E06"
cp "$BASE_DIR/Suits - 1x07 - Play The Man.HDTV.en.srt" "$SUBS_DIR/Suits.S01E07.720p.HDTV.x264/English.srt" && echo "✓ E07"
cp "$BASE_DIR/Suits - 1x08 - Identity Crisis.HDTV.L0L.en.srt" "$SUBS_DIR/Suits.S01E08.720p.HDTV.x264/English.srt" && echo "✓ E08"
cp "$BASE_DIR/Suits - 1x09 - Undefeated.HDTV.LOL.en.srt" "$SUBS_DIR/Suits.S01E09.720p.HDTV.x264/English.srt" && echo "✓ E09"
cp "$BASE_DIR/Suits - 1x10 - The Shelf Life.HDTV.L0L.en.srt" "$SUBS_DIR/Suits.S01E10.720p.HDTV.x264/English.srt" && echo "✓ E10"
cp "$BASE_DIR/Suits - 1x11 - Rules Of The Game.HDTV.LOL.en.srt" "$SUBS_DIR/Suits.S01E11.720p.HDTV.x264/English.srt" && echo "✓ E11"
cp "$BASE_DIR/Suits - 1x12 - Dog Fight.HDTV.en.srt" "$SUBS_DIR/Suits.S01E12.720p.HDTV.x264/English.srt" && echo "✓ E12"

echo ""
echo "Done! Verifying..."
ls -la "$SUBS_DIR"/*/English.srt 2>/dev/null | wc -l | xargs -I {} echo "{} files copied successfully"
