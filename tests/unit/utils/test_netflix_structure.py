import os
import shutil
import pytest
from pathlib import Path
from langflix.utils.path_utils import get_subtitle_folder, discover_subtitle_languages, find_media_subtitle_pairs

class TestNetflixFolderStructure:
    
    @pytest.fixture
    def netflix_structure(self, tmp_path):
        """
        Creates:
        show_name/
        ├── episodes_1.mp4
        ├── episodes_2.mp4
        └── Subs/
            ├── episodes_1/
            │   ├── Korean.srt
            │   └── English.srt
            └── episodes_2/
                └── Korean.srt
        """
        show_dir = tmp_path / "show_name"
        show_dir.mkdir()
        
        # Create videos
        (show_dir / "episodes_1.mp4").touch()
        (show_dir / "episodes_2.mp4").touch()
        
        # Create Subs
        subs_dir = show_dir / "Subs"
        subs_dir.mkdir()
        
        # Subs for Ep 1
        ep1_subs = subs_dir / "episodes_1"
        ep1_subs.mkdir()
        (ep1_subs / "Korean.srt").touch()
        (ep1_subs / "English.srt").touch()
        
        # Subs for Ep 2
        ep2_subs = subs_dir / "episodes_2"
        ep2_subs.mkdir()
        (ep2_subs / "Korean.srt").touch()
        
        return show_dir

    def test_get_subtitle_folder_ep1(self, netflix_structure):
        video_path = str(netflix_structure / "episodes_1.mp4")
        expected_subs = netflix_structure / "Subs" / "episodes_1"
        
        assert get_subtitle_folder(video_path) == expected_subs

    def test_get_subtitle_folder_ep2(self, netflix_structure):
        video_path = str(netflix_structure / "episodes_2.mp4")
        expected_subs = netflix_structure / "Subs" / "episodes_2"
        
        assert get_subtitle_folder(video_path) == expected_subs

    def test_discover_subtitle_languages(self, netflix_structure):
        video_path = str(netflix_structure / "episodes_1.mp4")
        langs = discover_subtitle_languages(video_path)
        
        assert "Korean" in langs
        assert "English" in langs
        assert len(langs) == 2
        
    def test_find_media_subtitle_pairs(self, netflix_structure):
        pairs = find_media_subtitle_pairs(str(netflix_structure))
        
        # Should find 2 pairs
        assert len(pairs) == 2
        
        # Convert to simple string sets for easy comparison
        found_videos = {p[0].name for p in pairs}
        found_subs = {p[1].name for p in pairs}
        
        assert "episodes_1.mp4" in found_videos
        assert "episodes_2.mp4" in found_videos
        assert "episodes_1" in found_subs # sub folder name
        assert "episodes_2" in found_subs # sub folder name
