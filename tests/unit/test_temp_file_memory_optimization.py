
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging
from langflix.utils.temp_file_manager import TempFileManager

logger = logging.getLogger(__name__)

class TestTempFileMemoryOptimization:
    
    @pytest.fixture
    def temp_manager(self, tmp_path):
        """Create a TempFileManager instance with a temporary base directory."""
        return TempFileManager(base_dir=tmp_path)

    def test_create_persistent_temp_file(self, temp_manager):
        """Verify persistent temp file creation and tracking."""
        # 1. Create file
        temp_path = temp_manager.create_persistent_temp_file(suffix=".test")
        
        # Verify it exists
        assert temp_path.exists()
        assert temp_path.stat().st_size == 0
        
        # Verify it is tracked
        assert temp_path in temp_manager.temp_files
        
        # 2. Write content
        content = b"Streamed content simulation"
        temp_path.write_bytes(content)
        assert temp_path.read_bytes() == content
        
        # 3. Verify it persists (no context manager exit to close it)
        assert temp_path.exists()

    def test_cleanup_removes_from_tracking(self, temp_manager):
        """Verify cleanup removes file from tracking to prevent memory leak."""
        temp_manager.temp_files.clear() # Reset tracking
        
        # Create 10 files
        files = []
        for i in range(10):
            files.append(temp_manager.create_persistent_temp_file(suffix=f".{i}"))
            
        assert len(temp_manager.temp_files) == 10
        
        # Cleanup one
        target = files[0]
        temp_manager.cleanup_temp_file(target)
        
        # Verify file is gone
        assert not target.exists()
        
        # Verify removed from tracking list
        assert len(temp_manager.temp_files) == 9
        assert target not in temp_manager.temp_files

    def test_cleanup_all_safety_net(self, temp_manager):
        """Verify cleanup_all handles persistent files if not manually cleaned."""
        temp_path = temp_manager.create_persistent_temp_file(suffix=".persistent")
        assert temp_path.exists()
        
        # Simulate server shutdown
        temp_manager.cleanup_all()
        
        assert not temp_path.exists()
        assert len(temp_manager.temp_files) == 0

    @patch("shutil.copyfileobj")
    def test_streaming_simulation(self, mock_copy, temp_manager):
        """Simulate the streaming pattern used in jobs.py."""
        # Mock UploadFile
        mock_upload_file = MagicMock()
        mock_upload_file.file = MagicMock() # The underlying spool
        
        # 1. Create temp file
        temp_path = temp_manager.create_persistent_temp_file(suffix=".mp4")
        
        # 2. Stream content (simulated)
        with open(temp_path, "wb") as buffer:
             # In real code: shutil.copyfileobj(video_file.file, buffer)
             buffer.write(b"Large video content")
        
        assert temp_path.stat().st_size > 0
        
        # 3. Pass to 'background task' (cleanup logic)
        path_str = str(temp_path)
        
        # ... logic inside background task ...
        p = Path(path_str)
        assert p.exists()
        temp_manager.cleanup_temp_file(p)
        assert not p.exists()
