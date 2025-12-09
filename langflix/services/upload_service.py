import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class UploadService:
    """Service for handling YouTube uploads."""
    
    def upload_videos(self, 
                     target_languages: List[str], 
                     paths: Dict, 
                     output_dir: Path):
        """Upload combined videos to YouTube."""
        from langflix.youtube.uploader import YouTubeUploader
        from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
        from langflix.youtube.video_manager import VideoFileManager
        
        try:
            uploader = YouTubeUploader()
            metadata_gen = YouTubeMetadataGenerator()
            video_manager = VideoFileManager(str(output_dir))
            
            if not uploader.authenticate():
                logger.error("YouTube authentication failed - cannot upload")
                return

            videos_to_upload: List[Tuple[str, Path]] = []
            
            # Scan for combined videos
            for lang in target_languages:
                lang_paths = paths.get('languages', {}).get(lang)
                if lang_paths:
                    # Look in 'long' dir or fallbacks
                    long_dir = lang_paths.get('long') # might be Path
                    if not long_dir: 
                         # Try finding it in structure
                         pass
                    
                    if long_dir and isinstance(long_dir, Path):
                        combo_path = long_dir / "combined.mkv"
                        if combo_path.exists():
                            videos_to_upload.append((lang, combo_path))
            
            if not videos_to_upload:
                logger.warning("No combined videos found for upload.")
                return

            for lang, video_path in videos_to_upload:
                try:
                    video_metadata = video_manager._extract_video_metadata(video_path)
                    if not video_metadata:
                         continue
                         
                    yt_metadata = metadata_gen.generate_metadata(
                        video_metadata,
                        target_language=lang,
                        privacy_status="private" 
                    )
                    
                    logger.info(f"Uploading {video_path.name} to YouTube ({lang})...")
                    result = uploader.upload_video(video_path, yt_metadata)
                    
                    if result.success:
                         logger.info(f"✅ Upload successful! Video ID: {result.video_id}")
                    else:
                         logger.error(f"❌ Upload failed: {result.error_message}")
                except Exception as e:
                     logger.error(f"Error uploading video {video_path}: {e}")
                     
        except Exception as e:
            logger.error(f"Upload process failed: {e}")
