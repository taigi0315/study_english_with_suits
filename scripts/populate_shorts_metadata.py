import json
import os
import sys
from pathlib import Path
from datetime import datetime
import re

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langflix.youtube.video_manager import VideoMetadata
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator

def update_metadata_files(directories):
    generator = YouTubeMetadataGenerator()
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory not found: {dir_path}")
            continue
            
        print(f"Scanning {dir_path}...")
        
        # Find all meta.json files
        meta_files = list(dir_path.glob("*.meta.json"))
        
        if not meta_files:
            print(f"No meta.json files found in {dir_path}")
            continue

        for meta_file in meta_files:
            try:
                # Load existing metadata
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                video_file = meta_file.with_name(meta_file.name.replace('.meta.json', '.mkv'))
                if not video_file.exists():
                   video_file = meta_file.with_name(meta_file.name.replace('.meta.json', '.mp4'))
                
                # If video file doesn't exist, use meta file path as proxy for filename extraction
                effective_path = video_file if video_file.exists() else meta_file
                
                # Extract episode from path
                match = re.search(r'(S\d+E\d+)', str(effective_path), flags=re.IGNORECASE)
                episode_str = match.group(1).upper() if match else "Unknown"
                
                # Show name inference
                show_name = data.get('show_name')
                if not show_name:
                    if "Business_Proposal" in str(effective_path):
                        show_name = "Business Proposal"
                    elif "Suits" in str(effective_path):
                        show_name = "Suits"
                    else:
                        show_name = "Korean Drama"

                # Detect learn_language from path
                path_str = str(effective_path)
                if "KOREAN" in path_str:
                    learn_language = "Korean"
                elif "English" in path_str or "Suits" in show_name:  # Suits is typically English
                     learn_language = "English"
                else:
                    learn_language = "English" # Default

                # Construct VideoMetadata
                video_meta = VideoMetadata(
                    path=str(effective_path),
                    filename=effective_path.name,
                    size_mb=0.0,
                    duration_seconds=60.0,
                    resolution="1080x1920",
                    format="mkv",
                    created_at=datetime.now(),
                    episode=episode_str,
                    expression=data.get('expression', ''),
                    expression_translation=data.get('expression_translation', ''),
                    title_translation=data.get('title_translation', ''),
                    catchy_keywords=data.get('catchy_keywords', []),
                    show_name=show_name,
                    video_type="short",
                    language=data.get('language', 'es'),
                    learn_language=learn_language,
                    expressions_included=[{"expression": data.get('expression', ''), "translation": data.get('expression_translation', ''), "catchy_keywords": data.get('catchy_keywords', []), "title_translation": data.get('title_translation', '')}]
                )
                
                # Generate new metadata
                target_lang = data.get('language', 'es')
                yt_meta = generator.generate_metadata(video_meta, target_language=target_lang)
                
                # Update data
                data['title'] = yt_meta.title
                # Remove newlines for easier manual copying
                data['description'] = yt_meta.description.replace('\n', ' ')
                data['tags'] = yt_meta.tags
                data['category_id'] = yt_meta.category_id
                data['show_name'] = show_name
                # Store learn_language for future reference (fixes tags on subsequent runs)
                data['learn_language'] = learn_language
                
                if 'generated_at' not in data:
                    data['generated_at'] = datetime.now().isoformat()

                # Write back
                with open(meta_file, 'w', encoding='utf-8') as f:
                    data = json.dumps(data, ensure_ascii=False, indent=2)
                    f.write(data)
                    
                print(f"Updated {meta_file.name} (Learn: {learn_language})")
                
            except Exception as e:
                print(f"Error processing {meta_file}: {e}")

if __name__ == "__main__":
    dirs = [
        "/Users/changikchoi/Documents/langflix/output/Business_Proposal/Business.Proposal.S01E03.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/es/shorts",
        "/Users/changikchoi/Documents/langflix/output/Business_Proposal/Business.Proposal.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/es/shorts",
        "/Users/changikchoi/Documents/langflix/output/Business_Proposal/Business.Proposal.S01E02.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/es/shorts"
    ]
    update_metadata_files(dirs)
