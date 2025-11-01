# [TICKET-003] Standardize Temporary File Management Across Codebase

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- 임시 파일이 제대로 정리되지 않으면 디스크 공간이 부족해질 수 있음
- 서버 재시작 시 누적된 임시 파일로 인한 문제 발생 가능
- 임시 파일 관리 불일치로 인한 버그 발생 가능

**Technical Impact:**
- 영향받는 모듈: `langflix/api/routes/jobs.py`, `langflix/main.py`, `langflix/core/video_editor.py`, `langflix/tts/`
- 예상 변경 파일: 8-10개
- 임시 파일 관리 코드 중복 제거

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** Multiple files

코드베이스 전체에 임시 파일 관리가 일관되지 않게 구현되어 있습니다:

1. **하드코딩된 경로 사용** (`langflix/api/routes/jobs.py:58-59`):
```python
temp_video_path = f"/tmp/{job_id}_video.mkv"
temp_subtitle_path = f"/tmp/{job_id}_subtitle.srt"
```

2. **tempfile 모듈 사용** (`langflix/main.py:428-430`):
```python
import tempfile
temp_dir = Path(tempfile.gettempdir())
video_output = temp_dir / f"temp_expression_{i+1:02d}_{safe_filename[:30]}.mkv"
```

3. **NamedTemporaryFile 사용** (`langflix/tts/lemonfox_client.py:204-210`):
```python
temp_file = tempfile.NamedTemporaryFile(
    delete=False, 
    suffix=suffix, 
    prefix="langflix_tts_"
)
output_path = Path(temp_file.name)
```

4. **VideoEditor의 _temp_files 추적** (`langflix/core/video_editor.py:37, 437-446`):
```python
self._temp_files = []  # Track temporary files for cleanup

def _cleanup_temp_files(self) -> None:
    """Clean up all registered temporary files"""
    for temp_file in self._temp_files:
        # cleanup logic
```

5. **수동 정리** (`langflix/api/routes/jobs.py:432-441`):
```python
# Clean up temporary files
try:
    os.unlink(temp_video_path)
    os.unlink(temp_subtitle_path)
    for temp_clip in temp_clip_files:
        if os.path.exists(temp_clip):
            os.unlink(temp_clip)
except Exception as e:
    logger.warning(f"Error cleaning up temp files: {e}")
```

### Root Cause Analysis
- 각 모듈이 독립적으로 개발되면서 일관된 임시 파일 관리 전략이 없었음
- Python의 `tempfile` 모듈을 제대로 활용하지 않음
- 컨텍스트 매니저나 리소스 관리 패턴을 사용하지 않음
- 예외 발생 시 정리 보장이 없음

### Evidence
- `langflix/api/routes/jobs.py:58-59`: 하드코딩된 `/tmp/` 경로
- `langflix/api/routes/joutes/jobs.py:432-441`: 수동 정리 코드
- `langflix/main.py:428-430`: tempfile.gettempdir() 직접 사용
- `langflix/core/video_editor.py:437-446`: 클래스 레벨 임시 파일 추적
- `langflix/tts/lemonfox_client.py:204-210`: NamedTemporaryFile 사용 (delete=False)
- 여러 곳에서 예외 발생 시 임시 파일 정리 실패 가능

## Proposed Solution

### Approach
1. **통합 TempFileManager 생성**: 임시 파일 생명주기를 중앙에서 관리하는 컨텍스트 매니저 생성
2. **컨텍스트 매니저 패턴 사용**: `with` 문을 사용하여 예외 발생 시에도 자동 정리 보장
3. **기존 코드 마이그레이션**: 모든 임시 파일 생성 코드를 새로운 매니저를 사용하도록 변경

### Implementation Details

#### Step 1: TempFileManager 생성
`langflix/utils/temp_file_manager.py` 생성:

```python
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import tempfile
import logging
import atexit
import shutil

logger = logging.getLogger(__name__)

class TempFileManager:
    """Centralized temporary file management with automatic cleanup."""
    
    def __init__(self, prefix: str = "langflix_", base_dir: Optional[Path] = None):
        """
        Initialize temp file manager.
        
        Args:
            prefix: Prefix for temporary files
            base_dir: Base directory for temp files (default: system temp dir)
        """
        self.prefix = prefix
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir())
        self.temp_files: list[Path] = []
        self.temp_dirs: list[Path] = []
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    @contextmanager
    def create_temp_file(
        self, 
        suffix: str = "", 
        prefix: Optional[str] = None,
        delete: bool = True
    ) -> Generator[Path, None, None]:
        """
        Create a temporary file with automatic cleanup.
        
        Args:
            suffix: File suffix (e.g., '.mkv', '.srt')
            prefix: Optional override for prefix
            delete: If True, delete file when context exits
        
        Yields:
            Path to temporary file
        """
        file_prefix = prefix or self.prefix
        temp_file = None
        
        try:
            # Use NamedTemporaryFile for cross-platform compatibility
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                prefix=file_prefix,
                dir=self.base_dir
            ) as f:
                temp_path = Path(f.name)
                self.temp_files.append(temp_path)
            
            yield temp_path
            
        finally:
            if delete and temp_path.exists():
                try:
                    temp_path.unlink()
                    self.temp_files.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
    
    @contextmanager
    def create_temp_dir(self, prefix: Optional[str] = None) -> Generator[Path, None, None]:
        """
        Create a temporary directory with automatic cleanup.
        
        Args:
            prefix: Optional override for prefix
        
        Yields:
            Path to temporary directory
        """
        dir_prefix = prefix or self.prefix
        
        try:
            temp_dir = Path(tempfile.mkdtemp(
                prefix=dir_prefix,
                dir=self.base_dir
            ))
            self.temp_dirs.append(temp_dir)
            
            yield temp_dir
            
        finally:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    self.temp_dirs.remove(temp_dir)
                    logger.debug(f"Cleaned up temp dir: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
    
    def register_file(self, file_path: Path) -> None:
        """Manually register a file for cleanup."""
        if file_path not in self.temp_files:
            self.temp_files.append(file_path)
    
    def cleanup_all(self) -> None:
        """Clean up all registered temporary files and directories."""
        # Clean up files
        for temp_file in self.temp_files[:]:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear()
        
        # Clean up directories
        for temp_dir in self.temp_dirs[:]:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temp dir: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
        
        self.temp_dirs.clear()

# Global instance
_global_manager: Optional[TempFileManager] = None

def get_temp_manager() -> TempFileManager:
    """Get global temporary file manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = TempFileManager()
    return _global_manager
```

#### Step 2: API 라우트 리팩토링
`langflix/api/routes/jobs.py` 수정:

```python
from langflix.utils.temp_file_manager import get_temp_manager

async def process_video_task(...):
    temp_manager = get_temp_manager()
    
    try:
        # Save uploaded files using temp manager
        with temp_manager.create_temp_file(suffix='.mkv', prefix=f'{job_id}_video') as temp_video_path:
            with open(temp_video_path, 'wb') as f:
                f.write(video_content)
            
            with temp_manager.create_temp_file(suffix='.srt', prefix=f'{job_id}_subtitle') as temp_subtitle_path:
                with open(temp_subtitle_path, 'wb') as f:
                    f.write(subtitle_content)
                
                # Process video using temp files
                # Files automatically cleaned up when context exits
                ...
```

#### Step 3: VideoEditor 리팩토링
`langflix/core/video_editor.py` 수정:

```python
from langflix.utils.temp_file_manager import get_temp_manager

class VideoEditor:
    def __init__(self, ...):
        self.temp_manager = get_temp_manager()
        # Remove self._temp_files
    
    def create_educational_sequence(self, ...):
        # Use temp manager instead of manual tracking
        with self.temp_manager.create_temp_file(suffix='.mkv') as temp_output:
            # Process video
            ...
            # File automatically cleaned up
```

#### Step 4: Main Pipeline 리팩토링
`langflix/main.py` 수정:

```python
from langflix.utils.temp_file_manager import get_temp_manager

class LangFlixPipeline:
    def __init__(self, ...):
        self.temp_manager = get_temp_manager()
    
    def _process_expressions(self):
        # Use temp manager for clip files
        with self.temp_manager.create_temp_file(suffix='.mkv', prefix='expression_') as video_output:
            # Extract clip
            ...
            # File automatically cleaned up after processing
```

### Alternative Approaches Considered

**Option 1: tempfile 모듈 직접 사용**
- 장점: 추가 코드 없음
- 단점: 예외 발생 시 정리 보장이 없음, 일관성 부족
- 선택하지 않은 이유: 안전하지 않음

**Option 2: 기존 VideoEditor의 _temp_files 패턴 확장**
- 장점: 기존 패턴 재사용
- 단점: 모든 클래스에 동일한 코드 중복 필요, atexit 등록 필요
- 선택하지 않은 이유: 코드 중복 증가

**Option 3: 선택된 접근 (TempFileManager)**
- 장점: 중앙 집중식 관리, 컨텍스트 매니저로 안전성 보장, 일관된 인터페이스
- 단점: 초기 구현 시간 필요
- 선택 이유: 최고의 안전성과 일관성

### Benefits
- **안전성 향상**: 예외 발생 시에도 임시 파일 자동 정리
- **일관성**: 모든 모듈에서 동일한 방식으로 임시 파일 관리
- **디스크 공간 보호**: 정리 누락으로 인한 디스크 부족 문제 방지
- **코드 간소화**: 수동 정리 코드 제거
- **디버깅 용이**: 임시 파일이 명확한 prefix를 가짐

### Risks & Considerations
- **Breaking Changes**: 기존 코드 변경으로 인한 잠재적 버그
- **성능**: 컨텍스트 매니저 오버헤드 (무시 가능)
- **마이그레이션**: 모든 임시 파일 생성 코드를 찾아 수정해야 함

## Testing Strategy

### Unit Tests
- `TempFileManager.create_temp_file()`: 파일 생성 및 자동 정리 테스트
- 예외 발생 시에도 파일이 정리되는지 검증
- `cleanup_all()`: 모든 파일 정리 검증

### Integration Tests
- 실제 비디오 처리 워크플로우에서 임시 파일이 올바르게 정리되는지 검증
- 여러 작업이 동시에 실행될 때 파일 충돌이 없는지 검증

## Files Affected

**새로 생성:**
- `langflix/utils/temp_file_manager.py` - 임시 파일 관리 유틸리티

**수정:**
- `langflix/api/routes/jobs.py` - 하드코딩된 경로와 수동 정리 코드 제거
- `langflix/main.py` - tempfile 직접 사용 대신 매니저 사용
- `langflix/core/video_editor.py` - `_temp_files` 제거, 매니저 사용
- `langflix/tts/lemonfox_client.py` - NamedTemporaryFile 대신 매니저 사용
- `langflix/tts/google_client.py` - 동일하게 수정 (만약 존재)
- `tests/api/test_jobs.py` - 임시 파일 정리 검증 추가
- `tests/integration/test_temp_file_cleanup.py` - 새로운 통합 테스트

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-001 (파이프라인 리팩토링과 함께 작업 시 시너지)

## References
- Python `tempfile` 모듈 문서: https://docs.python.org/3/library/tempfile.html
- Context Manager Pattern: https://docs.python.org/3/library/stdtypes.html#context-manager-types

## Architect Review Questions
**For the architect to consider:**
1. 전역 매니저 대신 의존성 주입 패턴이 더 나은가?
2. 임시 파일에 대한 로깅/모니터링이 필요한가?
3. 디스크 공간 할당량 관리가 필요한가?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- Critical for system stability - prevents disk space leaks
- Aligns with Resource Management Pattern - centralized resource lifecycle
- Synergy with TICKET-001 (can integrate temp file management in new service)
- Improves reliability - automatic cleanup even on exceptions
- Long-term maintenance benefit - consistent pattern across codebase

**Implementation Phase:** Phase 1 - Sprint 1 (Weeks 1-2)
**Sequence Order:** #3 in implementation queue (can work in parallel with TICKET-001)

**Architectural Guidance:**
- **Manager Design**: Use global singleton pattern initially (`get_temp_manager()`) - simple and sufficient
  - Can migrate to dependency injection later if needed (after TICKET-001 service layer is established)
- **Context Manager Pattern**: Emphasize `with` statement usage - ensures cleanup even on exceptions
- **Integration with TICKET-001**: Coordinate with TICKET-001 implementation - can use `TempFileManager` in new `VideoPipelineService`
- **Logging**: Add debug-level logging for temp file creation/cleanup - helpful for debugging but not verbose
- **Disk Quotas**: Not needed initially, but design allows for future quota tracking if required
- **Thread Safety**: Consider thread-safety if multiple workers process jobs concurrently

**Dependencies:**
- **Must complete first:** None
- **Should complete first:** Can coordinate with TICKET-001 (service layer can use this)
- **Blocks:** None
- **Related work:** TICKET-001 (can integrate this in new service), TICKET-005 (error handler can log temp file cleanup)

**Risk Mitigation:**
- Risk: Breaking existing temp file usage
  - Mitigation: Gradual migration - start with new code, migrate existing gradually
- Risk: Context manager overhead
  - Mitigation: Minimal overhead - Python's context managers are efficient
- Risk: File access after cleanup
  - Mitigation: Clear documentation, use `delete=False` option when file needs to persist
- **Rollback strategy:** Keep old patterns until fully tested - gradual migration

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] All new temp file creation uses `TempFileManager`
- [ ] Existing code migrated gradually (no breaking changes)
- [ ] Context managers used consistently (`with` statements)
- [ ] Thread-safety verified if concurrent processing implemented
- [ ] Integration tests verify cleanup even on exceptions
- [ ] Debug logging added for temp file lifecycle

**Alternative Approaches Considered:**
- Original proposal: Global `TempFileManager` with context managers ✅ Selected
- Alternative 1: Dependency injection - Deferred (can migrate later after service layer established)
- Alternative 2: Manual cleanup only - Rejected (error-prone, defeats purpose)
- **Selected approach:** Global manager with context managers - best balance of simplicity and safety

**Implementation Notes:**
- Start by: Creating `TempFileManager` utility module
- Watch out for: Files that need to persist beyond context (use `delete=False`)
- Coordinate with: TICKET-001 team if working in parallel (service layer integration)
- Reference: Existing patterns in `langflix/core/video_editor.py` (`_temp_files` tracking)

**Estimated Timeline:** 1-2 days (with testing)
**Recommended Owner:** Mid-level engineer (straightforward implementation)

## Success Criteria
How do we know this is successfully implemented?
- [ ] 모든 임시 파일 생성이 TempFileManager를 통해 이루어짐
- [ ] 하드코딩된 `/tmp/` 경로가 코드베이스에서 제거됨
- [ ] 예외 발생 시에도 임시 파일이 정리되는지 검증됨
- [ ] 통합 테스트에서 디스크 누수 없음
- [ ] 기존 기능 동작 유지

