# [TICKET-005] Consolidate Filename Sanitization Logic

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- 파일명 sanitization 로직이 일관되지 않아 파일명 충돌이나 예기치 않은 파일명 생성 가능
- 보안 측면에서 파일명 주입 공격 방어 로직이 일관되지 않음

**Technical Impact:**
- 영향받는 모듈: `langflix/main.py`, `langflix/api/routes/jobs.py`, `langflix/core/video_editor.py`, `langflix/subtitles/overlay.py`, `langflix/tts/lemonfox_client.py`, `langflix/tts/google_client.py`
- 예상 변경 파일: 6-8개
- 중복 코드 약 50줄 제거

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** Multiple files

파일명 sanitization 로직이 여러 곳에 중복되어 있습니다:

1. **langflix/main.py:727-732**:
```python
def _sanitize_filename(self, text: str) -> str:
    """Sanitize text for filename"""
    import re
    sanitized = re.sub(r'[^\w\s-]', '', text)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized[:50]
```

2. **langflix/api/routes/jobs.py:173, 214**:
```python
safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
safe_filename = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
```

3. **langflix/api/routes/jobs.py:330**:
```python
import re
safe_expression_name = re.sub(r'[^\w\s-]', '', expression.expression)
safe_expression_name = re.sub(r'[-\s]+', '_', safe_expression_name)
```

4. **langflix/core/video_editor.py** (grep 결과에 나타남, 실제 구현 확인 필요)

5. **기타 TTS 클라이언트들** (파일명 생성 시 sanitization 필요할 수 있음)

### Root Cause Analysis
- 각 모듈이 독립적으로 개발되면서 파일명 sanitization 로직이 중복됨
- 인라인 구현으로 인한 일관성 부족
- 길이 제한이 다름 (50자 vs 30자)
- 허용 문자 집합이 약간씩 다름

### Evidence
- `langflix/main.py:727-732`: 50자 제한, 정규식 사용
- `langflix/api/routes/jobs.py:173, 214`: 30자 제한, 문자 필터링 사용
- `langflix/api/routes/jobs.py:330`: 정규식 사용, 길이 제한 없음
- grep 결과: 7개 파일에서 sanitization 관련 코드 발견

## Proposed Solution

### Approach
1. **공통 유틸리티 함수 생성**: `langflix/utils/filename_utils.py`에 표준화된 sanitization 함수 생성
2. **모든 호출부 마이그레이션**: 기존 인라인 로직을 새 유틸리티 함수로 교체
3. **테스트 추가**: 다양한 입력에 대한 동작 검증

### Implementation Details

#### Step 1: Filename Utils 생성
`langflix/utils/filename_utils.py` 생성:

```python
"""
Filename sanitization utilities for safe file system operations.
"""
import re
from typing import Optional

# Maximum filename length (conservative for cross-platform compatibility)
MAX_FILENAME_LENGTH = 255  # Standard filesystem limit
DEFAULT_MAX_LENGTH = 100  # Reasonable default for our use case


def sanitize_filename(
    text: str,
    max_length: int = DEFAULT_MAX_LENGTH,
    replace_spaces: bool = True,
    allowed_extensions: Optional[list[str]] = None
) -> str:
    """
    Sanitize text to create a safe filename.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length of output (default: 100)
        replace_spaces: If True, replace spaces with underscores
        allowed_extensions: Optional list of allowed file extensions to preserve
    
    Returns:
        Sanitized filename-safe string
    
    Examples:
        >>> sanitize_filename("Hello World!")
        'Hello_World'
        >>> sanitize_filename("test.mp4", allowed_extensions=['.mp4'])
        'test.mp4'
        >>> sanitize_filename("very long filename that exceeds limit" * 10, max_length=50)
        'very_long_filename_that_exceeds_limit'
    """
    if not text:
        return "untitled"
    
    # Extract extension if preserving
    extension = ""
    base_name = text
    if allowed_extensions:
        for ext in allowed_extensions:
            if text.lower().endswith(ext.lower()):
                extension = ext
                base_name = text[:-len(ext)]
                break
    
    # Remove or replace invalid characters
    # Keep: alphanumeric, spaces, hyphens, underscores, dots (for extensions)
    if replace_spaces:
        # Replace spaces with underscores, then remove invalid chars
        sanitized = re.sub(r'[^\w\s.-]', '', base_name)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
    else:
        # Keep spaces but still remove invalid chars
        sanitized = re.sub(r'[^\w\s.-]', '', base_name)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Remove leading/trailing dots and underscores (invalid in some filesystems)
    sanitized = sanitized.strip('._-')
    
    # Enforce length limit (accounting for extension)
    max_base_length = max_length - len(extension)
    if len(sanitized) > max_base_length:
        sanitized = sanitized[:max_base_length]
    
    # Ensure not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized + extension


def sanitize_for_expression_filename(expression: str, max_length: int = 50) -> str:
    """
    Sanitize expression text specifically for use in filenames.
    
    This is a convenience wrapper for common expression filename use case.
    
    Args:
        expression: Expression text to sanitize
        max_length: Maximum length (default: 50 for expressions)
    
    Returns:
        Sanitized filename
    """
    return sanitize_filename(
        expression,
        max_length=max_length,
        replace_spaces=True
    )


def sanitize_for_context_video_name(expression: str) -> str:
    """
    Sanitize expression for context video filename.
    
    Consistent naming for context videos across the codebase.
    
    Args:
        expression: Expression text
    
    Returns:
        Sanitized filename (no extension)
    """
    return sanitize_for_expression_filename(expression, max_length=50)
```

#### Step 2: Main Pipeline 마이그레이션
`langflix/main.py` 수정:

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

class LangFlixPipeline:
    # Remove _sanitize_filename method
    
    def _process_expressions(self):
        # Replace:
        # safe_filename = self._sanitize_filename(expression.expression)
        # With:
        safe_filename = sanitize_for_expression_filename(expression.expression)
```

#### Step 3: API Routes 마이그레이션
`langflix/api/routes/jobs.py` 수정:

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename, sanitize_for_context_video_name

# Replace all instances:
# safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
# safe_filename = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
# With:
safe_filename = sanitize_for_expression_filename(expression.expression, max_length=30)

# Replace:
# safe_expression_name = re.sub(r'[^\w\s-]', '', expression.expression)
# safe_expression_name = re.sub(r'[-\s]+', '_', safe_expression_name)
# With:
safe_expression_name = sanitize_for_context_video_name(expression.expression)
```

### Alternative Approaches Considered

**Option 1: 가장 긴 함수를 선택하여 다른 곳에서 사용**
- 장점: 최소 변경
- 단점: 여전히 중복 존재, 일관성 부족
- 선택하지 않은 이유: 근본적 해결이 아님

**Option 2: 각 클래스에 메서드로 유지**
- 장점: 기존 코드 구조 유지
- 단점: 중복 계속 존재, 재사용 어려움
- 선택하지 않은 이유: DRY 원칙 위반

**Option 3: 선택된 접근 (공통 유틸리티)**
- 장점: 중복 제거, 일관성, 테스트 용이, 재사용성
- 단점: 초기 구현 시간 필요
- 선택 이유: 최선의 장기적 솔루션

### Benefits
- **일관성**: 모든 곳에서 동일한 sanitization 로직 사용
- **유지보수성**: 한 곳에서 수정하면 전체 반영
- **보안**: 파일명 주입 공격 방어 로직 일관화
- **테스트 용이성**: 단일 함수로 테스트 가능
- **재사용성**: 새로운 코드에서 쉽게 사용 가능

### Risks & Considerations
- **Breaking Changes**: 기존 생성된 파일명과 달라질 수 있음 (마이그레이션 필요 없음, 새로운 파일명만 영향)
- **호환성**: 기존 생성된 파일명과의 일치 여부는 중요하지 않음 (새로 생성되는 것만 영향)

## Testing Strategy

### Unit Tests
- `sanitize_filename()`: 다양한 입력에 대한 테스트
  - 특수 문자 포함
  - 긴 문자열 (길이 제한)
  - 빈 문자열
  - 유니코드 문자
  - 파일 확장자 보존
- `sanitize_for_expression_filename()`: 표현식 특화 테스트

### Integration Tests
- 실제 파일 생성 시 파일명이 올바르게 생성되는지 검증
- 파일 시스템에 실제로 저장 가능한 파일명인지 검증

### Regression Tests
- 기존 생성된 파일명과의 호환성 검증 (필요시)

## Files Affected

**새로 생성:**
- `langflix/utils/filename_utils.py` - 파일명 sanitization 유틸리티

**수정:**
- `langflix/main.py` - `_sanitize_filename` 메서드 제거, 유틸리티 사용
- `langflix/api/routes/jobs.py` - 인라인 sanitization 로직 제거, 유틸리티 사용
- `langflix/core/video_editor.py` - sanitization 로직이 있다면 유틸리티 사용
- `langflix/subtitles/overlay.py` - sanitization 로직이 있다면 유틸리티 사용
- `langflix/tts/lemonfox_client.py` - sanitization 로직이 있다면 유틸리티 사용
- `langflix/tts/google_client.py` - sanitization 로직이 있다면 유틸리티 사용

**테스트 추가:**
- `tests/unit/test_filename_utils.py` - 새로운 유닛 테스트

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-001 (파이프라인 리팩토링과 함께 작업 시 시너지)

## References
- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- Python pathlib documentation: https://docs.python.org/3/library/pathlib.html

## Architect Review Questions
**For the architect to consider:**
1. 파일명 길이 제한이 프로젝트 요구사항과 일치하는가?
2. 파일명 인코딩 고려가 필요한가? (예: UTF-8 vs ASCII)
3. 특정 파일 시스템 제약사항이 있는가? (예: Windows, macOS, Linux 호환성)

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- Code quality improvement - eliminates duplication across 7+ files
- Security enhancement - consistent filename injection protection
- Follows DRY principle - single source of truth for filename sanitization
- Low risk, high benefit - simple utility consolidation
- Unblocks better testing - single function to test thoroughly

**Implementation Phase:** Phase 2 - Sprint 2 (Weeks 3-4)
**Sequence Order:** #4 in implementation queue (after TICKET-001 establishes service layer)

**Architectural Guidance:**
- **File System Compatibility**: Ensure cross-platform compatibility (Windows, macOS, Linux)
  - Windows: Max 255 chars, reserved characters (`<>:"/\|?*`)
  - macOS: Similar restrictions, case-insensitive by default (but preserve case)
  - Linux: Fewer restrictions, but follow best practices
- **Encoding Strategy**: Use ASCII for filenames (UTF-8 can cause issues on some systems)
  - Consider transliteration for non-ASCII characters if needed
- **Length Limits**: 
  - Conservative default: 100 chars (accounts for directories, extensions)
  - Absolute max: 255 chars (filesystem limit)
  - Expression filenames: 50 chars (reasonable for expressions)
- **Extension Handling**: Preserve valid extensions when specified (`.mkv`, `.srt`, etc.)
- **Testing**: Comprehensive edge cases - special characters, long strings, Unicode, empty strings

**Dependencies:**
- **Must complete first:** TICKET-001 (service layer refactoring - easier to migrate after consolidation)
- **Should complete first:** None
- **Blocks:** None
- **Related work:** TICKET-001 (can use in new service layer)

**Risk Mitigation:**
- Risk: Filename format changes (backward compatibility)
  - Mitigation: New filenames only - existing files unaffected (acceptable change)
- Risk: Breaking existing file lookups
  - Mitigation: Test thoroughly - ensure expression matching still works (critical for TICKET-001 issue)
- Risk: Cross-platform issues
  - Mitigation: Test on multiple platforms, use conservative character set
- **Rollback strategy:** Simple revert - restore old code if issues arise

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Cross-platform tested (Windows, macOS, Linux)
- [ ] Expression matching verified (critical for video generation workflow)
- [ ] Edge cases tested (special chars, Unicode, long strings, empty)
- [ ] Existing functionality preserved (file lookups work correctly)
- [ ] Documentation includes examples for common use cases

**Alternative Approaches Considered:**
- Original proposal: Centralized utility with configurable options ✅ Selected
- Alternative 1: Keep duplication - Rejected (maintains technical debt)
- Alternative 2: Max length only, no sanitization - Rejected (security risk)
- **Selected approach:** Centralized utility - best balance of safety and flexibility

**Implementation Notes:**
- Start by: Creating comprehensive test suite for edge cases
- Watch out for: Expression matching (must match exactly with job creation sanitization)
- Coordinate with: TICKET-001 team if overlapping (filename usage in pipeline)
- Reference: `langflix/core/video_editor.py::_sanitize_filename()` for existing pattern, `langflix/api/routes/jobs.py` for job creation usage

**Estimated Timeline:** < 1 day (with comprehensive testing)
**Recommended Owner:** Any developer (straightforward utility)

## Success Criteria
How do we know this is successfully implemented?
- [ ] 모든 파일명 sanitization이 공통 유틸리티를 통해 이루어짐
- [ ] 중복된 sanitization 코드가 코드베이스에서 제거됨
- [ ] 단위 테스트로 다양한 엣지 케이스 검증 완료
- [ ] 실제 파일 생성 시 안전한 파일명이 생성됨
- [ ] 기존 기능 동작 유지

