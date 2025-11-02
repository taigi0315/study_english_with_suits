# [TICKET-011] Add Database Session Context Manager for Consistent Resource Management

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
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- 수동 세션 관리로 인한 리소스 누수 가능성
- 예외 발생 시 세션 정리 누락 가능성
- 코드 일관성 부족으로 인한 유지보수 어려움

**Technical Impact:**
- 영향받는 모듈: `langflix/db/session.py`, `langflix/main.py`, `langflix/youtube/`
- 예상 변경 파일: 3-5개
- Breaking changes: 없음 (기존 코드는 계속 동작, 새로운 패턴 제공)

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/db/session.py:59-61`, `langflix/main.py:599-632`

현재 데이터베이스 세션 관리가 수동으로 이루어지고 있습니다:

```python
# langflix/main.py:605-628
db = db_manager.get_session()
try:
    # ... database operations ...
    db.commit()
except Exception as e:
    db.rollback()
finally:
    db.close()
```

**문제점:**
1. 매번 try-except-finally 패턴을 수동으로 작성해야 함
2. `db.close()` 호출 누락 시 리소스 누수 발생 가능
3. 예외 발생 시 rollback 처리가 일관되지 않을 수 있음
4. 코드 중복 (여러 곳에서 동일한 패턴 반복)
5. 문서(`docs/db/README_eng.md:216`)에서도 수동 `db.close()` 호출 예시를 보여주고 있음

### Root Cause Analysis
- SQLAlchemy Session이 context manager를 지원하지만 명시적으로 사용하지 않음
- 초기 구현 시 단순한 접근 방식 선택
- 리소스 관리 패턴의 일관성 부족

### Evidence
- `langflix/main.py:605-628`: 수동 try-except-finally 패턴
- `langflix/main.py:262-281`: 또 다른 수동 세션 관리
- `docs/db/README_eng.md:207-216`: 수동 `db.close()` 예시
- `tests/integration/test_db_integration.py`: 테스트에서도 수동 close() 호출
- `langflix/youtube/web_ui.py`: 여러 곳에서 수동 세션 관리

## Proposed Solution

### Approach
1. **Context Manager 추가**: `DatabaseManager`에 `session()` context manager 메서드 추가
2. **기존 코드 리팩토링**: 수동 세션 관리 코드를 context manager 사용으로 변경
3. **문서 업데이트**: README에 context manager 사용법 추가
4. **하위 호환성 유지**: 기존 `get_session()` 메서드는 계속 지원 (선택적 사용)

### Implementation Details

#### Step 1: Add Context Manager to DatabaseManager
```python
# langflix/db/session.py
from contextlib import contextmanager
from typing import Generator

class DatabaseManager:
    """Database connection manager."""
    
    # ... existing code ...
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database session.
        
        Automatically handles commit, rollback, and close.
        
        Usage:
            with db_manager.session() as db:
                # ... database operations ...
                # Commit happens automatically on success
        
        Yields:
            Session: Database session
        """
        if not self._initialized:
            self.initialize()
        
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_session(self) -> Session:
        """Get database session (legacy method, use session() context manager instead)."""
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()
```

#### Step 2: Refactor Existing Code
```python
# langflix/main.py:599-632
def _save_expressions_to_database(self, media_id: str):
    """Save expressions to database."""
    if not DB_AVAILABLE or not settings.get_database_enabled():
        return
    
    try:
        with db_manager.session() as db:
            for expression in self.expressions:
                try:
                    ExpressionCRUD.create_from_analysis(
                        db=db,
                        media_id=media_id,
                        analysis_data=expression
                    )
                    logger.debug(f"Saved expression to database: {expression.expression}")
                except Exception as e:
                    logger.error(f"Failed to save expression '{expression.expression}': {e}")
                    # Continue with next expression - transaction will rollback if needed
            
            logger.info(f"Saved {len(self.expressions)} expressions to database")
    except Exception as e:
        logger.error(f"Database error during expression save: {e}")
        logger.warning("⚠️ Failed to save expressions to database. Pipeline will continue.")
        # Don't raise - allow pipeline to continue
```

#### Step 3: Update Documentation
```python
# docs/db/README_eng.md
### Recommended: Using Context Manager

```python
from langflix.db.session import db_manager

# Recommended approach: automatic commit/rollback/close
with db_manager.session() as db:
    media = MediaCRUD.create(
        db,
        show_name="Suits",
        episode_name="S01E01",
        language_code="ko",
        subtitle_file_path="subtitles/s01e01.srt",
        video_file_path="media/s01e01.mp4"
    )
    # Commit happens automatically on success
    # Rollback happens automatically on exception
    # Close happens automatically in finally block
```

### Legacy: Manual Session Management

```python
# Still supported but not recommended
db = db_manager.get_session()
try:
    media = MediaCRUD.create(db, ...)
    db.commit()
except Exception:
    db.rollback()
finally:
    db.close()
```
```

### Alternative Approaches Considered
- **Option 1**: SQLAlchemy의 기본 sessionmaker를 context manager로 사용 - Rejected (DatabaseManager 래퍼를 통한 일관성 유지 필요)
- **Option 2**: 전역 함수로 context manager 제공 - Rejected (DatabaseManager 클래스 메서드가 더 명확)
- **Option 3**: 선택한 접근법 - DatabaseManager에 context manager 메서드 추가, 기존 get_session() 유지

### Benefits
- **자동 리소스 관리**: commit, rollback, close 자동 처리
- **코드 간결성**: try-except-finally 패턴 제거
- **일관성**: 모든 데이터베이스 작업에서 동일한 패턴 사용
- **안전성**: 예외 발생 시 자동 rollback 및 리소스 정리
- **가독성**: Python의 표준 context manager 패턴 사용

### Risks & Considerations
- **Breaking changes**: 없음 (기존 get_session() 메서드는 유지)
- **기존 코드 마이그레이션**: 점진적 마이그레이션 가능
- **에러 처리**: context manager 내부 예외는 자동 rollback되지만 외부로 전파됨

## Testing Strategy
- **Unit Tests**:
  - Context manager 정상 동작 테스트 (commit 확인)
  - 예외 발생 시 rollback 테스트
  - 세션 자동 close 테스트
  - 중첩 context manager 지원 여부 테스트
- **Integration Tests**:
  - 실제 데이터베이스 작업에서 context manager 사용 테스트
  - 기존 코드 리팩토링 후 통합 테스트 통과 확인
- **Error Scenarios**:
  - 예외 발생 시 롤백 확인
  - 리소스 정리 확인 (세션이 닫혔는지)

## Files Affected
- `langflix/db/session.py` - `session()` context manager 메서드 추가
- `langflix/main.py` - `_save_expressions_to_database()` 리팩토링
- `langflix/main.py` - `run()` 메서드 내 데이터베이스 초기화 부분 리팩토링
- `langflix/youtube/web_ui.py` - 세션 관리 코드 리팩토링 (선택적)
- `tests/integration/test_db_integration.py` - 테스트 코드 업데이트
- `docs/db/README_eng.md` - Context manager 사용법 추가
- `docs/db/README_kor.md` - Context manager 사용법 추가

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-010 (API dependencies 구현 시 context manager 활용)

## References
- Related documentation: `docs/db/README_eng.md`, `docs/db/README_kor.md`
- Python contextlib: https://docs.python.org/3/library/contextlib.html
- SQLAlchemy session management: https://docs.sqlalchemy.org/en/20/orm/session_basics.html

## Architect Review Questions
**For the architect to consider:**
1. 모든 기존 코드를 즉시 마이그레이션해야 하는가, 아니면 점진적으로 진행할 수 있는가?
2. API dependencies(TICKET-010)와의 통합 시 context manager 패턴이 충돌하지 않는가?
3. YouTube 모듈의 세션 관리도 리팩토링해야 하는가?

## Success Criteria
How do we know this is successfully implemented?
- [ ] `db_manager.session()` context manager가 정상 동작
- [ ] 자동 commit/rollback/close가 정상 작동
- [ ] 기존 코드가 리팩토링되어 context manager 사용
- [ ] 모든 관련 테스트 통과
- [ ] 문서에 context manager 사용법 추가됨
- [ ] 리소스 누수 없음 (세션 정리 확인)
- [ ] 예외 발생 시 적절한 rollback 처리

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- Context manager는 Python의 자동 리소스 관리 표준 패턴
- 수동 세션 관리 코드 중복을 제거해 유지보수성 향상
- TICKET-010의 `get_db()` 구현 시 이 패턴 활용

**Implementation Phase:** Phase 0 - Immediate
**Sequence Order:** #2 (TICKET-010 이전에 완료되면 더 좋음)

**Architectural Guidance:**
- `session()` context manager 추가, `get_session()` 유지
- 점진적 마이그레이션, 즉시 전환 불필요
- SQLAlchemy Session은 중첩 context manager 지원

**Dependencies:**
- **Must complete first:** 없음
- **Should complete first:** 없음
- **Blocks:** 없음
- **Related work:** TICKET-010 (구현 시 `get_db()`에서 `session()` 활용)

**Risk Mitigation:**
- 하위 호환 유지로 불안 안정성 높음
- 기존 테스트 연동
- 점진 마이그레이션으로 리스크 낮음

**Alternative Approaches Considered:**
- SQLAlchemy 기본 sessionmaker: `DatabaseManager` 래퍼 필요
- 전역 함수: 메서드가 명확
- **Selected approach:** `DatabaseManager.session()`, `get_session()` 유지

**Implementation Notes:**
- `langflix/db/session.py`에 `@contextmanager session()` 추가
- `langflix/main.py`의 `_save_expressions_to_database()` 마이그레이션
- `langflix/youtube/`는 선택 사항
- 문서: context manager 사용 권장

**Estimated Timeline:** 반일 미만
**Recommended Owner:** 중급+

---

