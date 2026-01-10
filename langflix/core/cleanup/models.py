"""
Data models and enums for file system cleanup and management.

This module defines the core data structures used throughout the cleanup system,
including job contexts, manifests, directory structures, and cleanup policies.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


class JobType(Enum):
    """Types of video generation jobs."""
    SHORT_FORM = "short_form"
    LONG_FORM = "long_form"
    EXPRESSION_ONLY = "expression_only"
    SLIDES_ONLY = "slides_only"


class FileType(Enum):
    """Types of files created during video processing."""
    TEMP_VIDEO = "temp_video"
    TEMP_SLIDE = "temp_slide"
    TEMP_EXPRESSION = "temp_expression"
    TEMP_AUDIO = "temp_audio"
    TEMP_SUBTITLE = "temp_subtitle"
    FINAL_VIDEO = "final_video"
    FINAL_SLIDE = "final_slide"
    METADATA = "metadata"
    MANIFEST = "manifest"
    LOG = "log"


class DirectoryType(Enum):
    """Types of directories created during processing."""
    BASE = "base"
    TEMP = "temp"
    SLIDES = "slides"
    EXPRESSIONS = "expressions"
    SHORTS = "shorts"
    LONG_FORM = "long_form"
    METADATA = "metadata"
    SUBTITLES = "subtitles"


class JobStatus(Enum):
    """Status of a video generation job."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEANING_UP = "cleaning_up"
    CLEANED = "cleaned"


@dataclass
class CleanupPolicy:
    """Configuration for cleanup behavior."""
    enabled: bool = True
    retention_hours: int = 24
    file_types_to_clean: List[FileType] = field(default_factory=lambda: [
        FileType.TEMP_VIDEO,
        FileType.TEMP_SLIDE,
        FileType.TEMP_EXPRESSION,
        FileType.TEMP_AUDIO,
        FileType.TEMP_SUBTITLE,
    ])
    preserve_on_failure: bool = True
    debug_mode_disables: bool = True

    def should_clean_file_type(self, file_type: FileType) -> bool:
        """Check if a file type should be cleaned up."""
        return file_type in self.file_types_to_clean

    def is_cleanup_disabled_for_debug(self, debug_mode: bool) -> bool:
        """Check if cleanup is disabled due to debug mode."""
        return debug_mode and self.debug_mode_disables

    def validate(self) -> None:
        """Validate the cleanup policy configuration."""
        if self.retention_hours < 0:
            raise ValueError("Retention hours must be non-negative")
        
        if not isinstance(self.file_types_to_clean, list):
            raise ValueError("file_types_to_clean must be a list")
        
        # Ensure all file types are valid
        for file_type in self.file_types_to_clean:
            if not isinstance(file_type, FileType):
                raise ValueError(f"Invalid file type: {file_type}")


@dataclass
class DirectoryStructure:
    """Structure of directories for a job."""
    base_dir: Path
    temp_dir: Optional[Path] = None
    slides_dir: Optional[Path] = None
    expressions_dir: Optional[Path] = None
    shorts_dir: Optional[Path] = None
    long_form_dir: Optional[Path] = None
    metadata_dir: Optional[Path] = None

    def get_all_directories(self) -> List[Path]:
        """Get all non-None directories."""
        dirs = []
        for dir_path in [
            self.base_dir,
            self.temp_dir,
            self.slides_dir,
            self.expressions_dir,
            self.shorts_dir,
            self.long_form_dir,
            self.metadata_dir,
        ]:
            if dir_path is not None:
                dirs.append(dir_path)
        return dirs

    def get_directory_by_type(self, dir_type: DirectoryType) -> Optional[Path]:
        """Get directory path by type."""
        mapping = {
            DirectoryType.BASE: self.base_dir,
            DirectoryType.TEMP: self.temp_dir,
            DirectoryType.SLIDES: self.slides_dir,
            DirectoryType.EXPRESSIONS: self.expressions_dir,
            DirectoryType.SHORTS: self.shorts_dir,
            DirectoryType.LONG_FORM: self.long_form_dir,
            DirectoryType.METADATA: self.metadata_dir,
        }
        return mapping.get(dir_type)

    def validate(self) -> None:
        """Validate the directory structure."""
        if not self.base_dir:
            raise ValueError("base_dir is required")
        
        # Ensure all paths are Path objects
        for attr_name in ['base_dir', 'temp_dir', 'slides_dir', 'expressions_dir', 
                         'shorts_dir', 'long_form_dir', 'metadata_dir']:
            value = getattr(self, attr_name)
            if value is not None and not isinstance(value, Path):
                raise ValueError(f"{attr_name} must be a Path object")


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    success: bool
    files_removed: List[Path] = field(default_factory=list)
    files_failed: List[Path] = field(default_factory=list)
    directories_removed: List[Path] = field(default_factory=list)
    directories_failed: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_size_freed: int = 0  # bytes

    @property
    def total_files_processed(self) -> int:
        """Total number of files processed."""
        return len(self.files_removed) + len(self.files_failed)

    @property
    def total_directories_processed(self) -> int:
        """Total number of directories processed."""
        return len(self.directories_removed) + len(self.directories_failed)

    @property
    def has_failures(self) -> bool:
        """Check if there were any failures."""
        return len(self.files_failed) > 0 or len(self.directories_failed) > 0

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def merge(self, other: 'CleanupResult') -> 'CleanupResult':
        """Merge another cleanup result into this one."""
        return CleanupResult(
            success=self.success and other.success,
            files_removed=self.files_removed + other.files_removed,
            files_failed=self.files_failed + other.files_failed,
            directories_removed=self.directories_removed + other.directories_removed,
            directories_failed=self.directories_failed + other.directories_failed,
            errors=self.errors + other.errors,
            total_size_freed=self.total_size_freed + other.total_size_freed,
        )


@dataclass
class JobManifest:
    """Manifest tracking all files and directories for a job."""
    job_id: str
    created_at: datetime
    job_type: JobType
    files: Dict[FileType, List[Path]] = field(default_factory=dict)
    directories: Dict[DirectoryType, List[Path]] = field(default_factory=dict)
    status: JobStatus = JobStatus.CREATED
    cleanup_policy: Optional[CleanupPolicy] = None

    def add_file(self, file_path: Path, file_type: FileType) -> None:
        """Add a file to the manifest."""
        if file_type not in self.files:
            self.files[file_type] = []
        if file_path not in self.files[file_type]:
            self.files[file_type].append(file_path)

    def add_directory(self, dir_path: Path, dir_type: DirectoryType) -> None:
        """Add a directory to the manifest."""
        if dir_type not in self.directories:
            self.directories[dir_type] = []
        if dir_path not in self.directories[dir_type]:
            self.directories[dir_type].append(dir_path)

    def remove_file(self, file_path: Path) -> bool:
        """Remove a file from the manifest. Returns True if found and removed."""
        for file_type, paths in self.files.items():
            if file_path in paths:
                paths.remove(file_path)
                return True
        return False

    def remove_directory(self, dir_path: Path) -> bool:
        """Remove a directory from the manifest. Returns True if found and removed."""
        for dir_type, paths in self.directories.items():
            if dir_path in paths:
                paths.remove(dir_path)
                return True
        return False

    def get_files_by_type(self, file_type: FileType) -> List[Path]:
        """Get all files of a specific type."""
        return self.files.get(file_type, []).copy()

    def get_directories_by_type(self, dir_type: DirectoryType) -> List[Path]:
        """Get all directories of a specific type."""
        return self.directories.get(dir_type, []).copy()

    def get_all_files(self) -> List[Path]:
        """Get all files in the manifest."""
        all_files = []
        for paths in self.files.values():
            all_files.extend(paths)
        return all_files

    def get_all_directories(self) -> List[Path]:
        """Get all directories in the manifest."""
        all_dirs = []
        for paths in self.directories.values():
            all_dirs.extend(paths)
        return all_dirs

    def get_cleanable_files(self) -> List[Path]:
        """Get files that should be cleaned up based on cleanup policy."""
        if not self.cleanup_policy:
            return []
        
        cleanable = []
        for file_type, paths in self.files.items():
            if self.cleanup_policy.should_clean_file_type(file_type):
                cleanable.extend(paths)
        return cleanable

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for serialization."""
        # Convert cleanup policy to dict with enum values
        cleanup_policy_dict = None
        if self.cleanup_policy:
            cleanup_policy_dict = {
                'enabled': self.cleanup_policy.enabled,
                'retention_hours': self.cleanup_policy.retention_hours,
                'file_types_to_clean': [ft.value for ft in self.cleanup_policy.file_types_to_clean],
                'preserve_on_failure': self.cleanup_policy.preserve_on_failure,
                'debug_mode_disables': self.cleanup_policy.debug_mode_disables,
            }
        
        return {
            'job_id': self.job_id,
            'created_at': self.created_at.isoformat(),
            'job_type': self.job_type.value,
            'files': {
                file_type.value: [str(path) for path in paths]
                for file_type, paths in self.files.items()
            },
            'directories': {
                dir_type.value: [str(path) for path in paths]
                for dir_type, paths in self.directories.items()
            },
            'status': self.status.value,
            'cleanup_policy': cleanup_policy_dict,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobManifest':
        """Create manifest from dictionary."""
        # Parse cleanup policy
        cleanup_policy = None
        if data.get('cleanup_policy'):
            policy_data = data['cleanup_policy']
            cleanup_policy = CleanupPolicy(
                enabled=policy_data.get('enabled', True),
                retention_hours=policy_data.get('retention_hours', 24),
                file_types_to_clean=[
                    FileType(ft) for ft in policy_data.get('file_types_to_clean', [])
                ],
                preserve_on_failure=policy_data.get('preserve_on_failure', True),
                debug_mode_disables=policy_data.get('debug_mode_disables', True),
            )

        # Parse files
        files = {}
        for file_type_str, paths_str in data.get('files', {}).items():
            file_type = FileType(file_type_str)
            files[file_type] = [Path(path) for path in paths_str]

        # Parse directories
        directories = {}
        for dir_type_str, paths_str in data.get('directories', {}).items():
            dir_type = DirectoryType(dir_type_str)
            directories[dir_type] = [Path(path) for path in paths_str]

        return cls(
            job_id=data['job_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            job_type=JobType(data['job_type']),
            files=files,
            directories=directories,
            status=JobStatus(data.get('status', 'created')),
            cleanup_policy=cleanup_policy,
        )

    def save_to_file(self, file_path: Path) -> None:
        """Save manifest to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: Path) -> 'JobManifest':
        """Load manifest from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def validate(self) -> None:
        """Validate the manifest."""
        if not self.job_id:
            raise ValueError("job_id is required")
        
        if not isinstance(self.job_type, JobType):
            raise ValueError("job_type must be a JobType enum")
        
        if not isinstance(self.status, JobStatus):
            raise ValueError("status must be a JobStatus enum")
        
        # Validate file types and paths
        for file_type, paths in self.files.items():
            if not isinstance(file_type, FileType):
                raise ValueError(f"Invalid file type: {file_type}")
            for path in paths:
                if not isinstance(path, Path):
                    raise ValueError(f"File path must be Path object: {path}")
        
        # Validate directory types and paths
        for dir_type, paths in self.directories.items():
            if not isinstance(dir_type, DirectoryType):
                raise ValueError(f"Invalid directory type: {dir_type}")
            for path in paths:
                if not isinstance(path, Path):
                    raise ValueError(f"Directory path must be Path object: {path}")
        
        # Validate cleanup policy if present
        if self.cleanup_policy:
            self.cleanup_policy.validate()


@dataclass
class JobContext:
    """Context for a video generation job."""
    job_id: str
    job_type: JobType
    start_time: datetime
    output_dir: Path
    manifest_path: Path
    directories: DirectoryStructure
    temp_files: List[Path] = field(default_factory=list)
    final_outputs: List[Path] = field(default_factory=list)

    def add_temp_file(self, file_path: Path) -> None:
        """Add a temporary file to track."""
        if file_path not in self.temp_files:
            self.temp_files.append(file_path)

    def add_final_output(self, file_path: Path) -> None:
        """Add a final output file to track."""
        if file_path not in self.final_outputs:
            self.final_outputs.append(file_path)

    def remove_temp_file(self, file_path: Path) -> bool:
        """Remove a temporary file from tracking. Returns True if found and removed."""
        if file_path in self.temp_files:
            self.temp_files.remove(file_path)
            return True
        return False

    def get_all_tracked_files(self) -> List[Path]:
        """Get all tracked files (temp + final)."""
        return self.temp_files + self.final_outputs

    def validate(self) -> None:
        """Validate the job context."""
        if not self.job_id:
            raise ValueError("job_id is required")
        
        if not isinstance(self.job_type, JobType):
            raise ValueError("job_type must be a JobType enum")
        
        if not isinstance(self.output_dir, Path):
            raise ValueError("output_dir must be a Path object")
        
        if not isinstance(self.manifest_path, Path):
            raise ValueError("manifest_path must be a Path object")
        
        # Validate directory structure
        self.directories.validate()
        
        # Validate file paths
        for file_path in self.temp_files + self.final_outputs:
            if not isinstance(file_path, Path):
                raise ValueError(f"File path must be Path object: {file_path}")