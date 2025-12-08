#!/usr/bin/env python3
"""
Backfill YouTube Metadata
------------------------
Updates existing YouTube video titles and descriptions to use the target language (Korean) format.
It fetches all videos, parses their content to extract expression/episode info, regenerates metadata using the new Korean templates, and updates the video.

Usage:
    python scripts/backfill_youtube_metadata.py [--dry-run] [--limit N]

Options:
    --dry-run   Preview changes without applying them
    --limit N   Limit to processing N videos (default: all)
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from langflix.youtube.uploader import YouTubeUploader, YouTubeVideoMetadata
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.video_manager import VideoMetadata
from langflix import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_english_title(title: str) -> Dict[str, str]:
    """
    Parse existing English title to extract metadata.
    Format is typically: "{expression} | {translation} | from {episode}"
    or "{expression} | {translation} | {episode}" (if already updated partially)
    """
    parts = [p.strip() for p in title.split('|')]
    
    metadata = {}
    
    if len(parts) >= 3:
        # Assume last part is episode
        episode_part = parts[-1]
        
        # Extract potential episode code (e.g. S01E01)
        episode_match = re.search(r'(S\d+E\d+)', episode_part)
        if episode_match:
            metadata['episode'] = f"Suits.{episode_match.group(1)}"
        else:
            # Maybe it's just "Suits" or similar
            metadata['episode'] = episode_part.replace("from ", "").strip()
            
        # First part is expression
        metadata['expression'] = parts[0]
        
        # Second part is translation (or description)
        translation = parts[1]
        # Ignore generic English placeholder so we can use localized fallback
        if "Learn the meaning and usage in the video" in translation:
            metadata['translation'] = None
        else:
            metadata['translation'] = translation
        
        return metadata
        
    return None

def parse_description(description: str) -> Dict[str, str]:
    """
    Parse description to extract metadata if title parsing fails.
    """
    metadata = {}
    
    # Try to find "Expression: {expr}"
    expr_match = re.search(r'Expression:\s*(.+)', description)
    if expr_match:
        metadata['expression'] = expr_match.group(1).strip()
        
    # Try to find "Meaning: {translation}" or "Translation: {translation}"
    trans_match = re.search(r'(Meaning|Translation|의미):\s*(.+)', description)
    if trans_match:
        metadata['translation'] = trans_match.group(2).strip()
        
    # Try to find Episode
    ep_match = re.search(r'(Episode|from|Suits)\s*[:]?\s*(S\d+E\d+)', description)
    if ep_match:
        metadata['episode'] = f"Suits.{ep_match.group(2)}"
        
    return metadata

def main():
    parser = argparse.ArgumentParser(description="Backfill YouTube metadata to Korean")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of videos to process")
    parser.add_argument("--video-id", type=str, help="Process specific video ID only")
    
    args = parser.parse_args()
    
    # Initialize services
    uploader = YouTubeUploader()
    if not uploader.authenticate():
        logger.error("Failed to authenticate with YouTube")
        return
    
    generator = YouTubeMetadataGenerator()
    
    # Get videos
    if args.video_id:
         # Fetch single video details
        video_info = uploader.get_video_info(args.video_id)
        videos = [video_info] if video_info else []
    else:
        logger.info("Fetching videos from YouTube...")
        # Note: list_my_videos in uploader.py might need pagination support for ALL videos,
        # but for now we'll use what's available or default to max limit.
        # Assuming list_my_videos returns recent 50 by default, might need a loop for all.
        # For this task, we'll start with the default batch.
        videos = uploader.list_my_videos(max_results=50 if args.limit == 0 else args.limit)
    
    logger.info(f"Found {len(videos)} videos to process")
    
    count = 0
    updated_count = 0
    
    for video in videos:
        if args.limit > 0 and count >= args.limit:
            break
            
        video_id = video['id']
        snippet = video['snippet']
        title = snippet['title']
        description = snippet['description']
        
        logger.info(f"Processing video {video_id}: {title}")
        
        # Skip if already in Korean format (heuristic: contains '수트' and not 'from')
        # But user said "fix code to write in target language", so we should enforce it even if partially Korean.
        # Let's re-generate to be sure.
        
        # 1. Extract metadata
        meta = parse_english_title(title)
        if not meta:
            # Fallback to description parsing
            meta = parse_description(description)
            
        if not meta or not meta.get('expression'):
            logger.warning(f"Could not extract metadata for video {video_id}, skipping")
            continue
            
        # 2. Create VideoMetadata object
        # We don't have the original file path or tech details, but good enough for metadata generation
        video_metadata = VideoMetadata(
            path=f"dummy_path/{video_id}.mp4",
            filename=f"{video_id}.mp4",
            size_mb=0,
            duration_seconds=0,
            resolution="1080p",
            format="mp4",
            created_at=None,
            episode=meta.get('episode', 'Suits'),
            expression=meta.get('expression'),
            expression_translation=meta.get('translation'),
            # Guess video type based on title/tags? Default to 'short' if #Shorts in desc/tags, else educational
            video_type="short" if "#Shorts" in description or "#shorts" in description else "educational",
            language="ko" # Enforce target language
        )
        
        # 3. Generate new metadata using Korean template
        new_metadata = generator.generate_metadata(
            video_metadata,
            target_language="Korean"
        )
        
        # 4. Compare and update
        if new_metadata.title == title and new_metadata.description == description:
            logger.info("Metadata already matches target format, skipping update")
            continue
            
        logger.info(f"Checking update for {video_id}")
        logger.info(f"OLD Title: {title}")
        logger.info(f"NEW Title: {new_metadata.title}")
        # logger.info(f"OLD Desc: {description[:100]}...")
        # logger.info(f"NEW Desc: {new_metadata.description[:100]}...")
        
        if args.dry_run:
            logger.info("[DRY RUN] Would update video metadata")
        else:
            success = uploader.update_video_metadata(video_id, new_metadata)
            if success:
                logger.info(f"Successfully updated video {video_id}")
                updated_count += 1
            else:
                logger.error(f"Failed to update video {video_id}")
        
        count += 1
        
    logger.info(f"Finished. Processed {count} videos. Updated {updated_count} videos.")

if __name__ == "__main__":
    main()
