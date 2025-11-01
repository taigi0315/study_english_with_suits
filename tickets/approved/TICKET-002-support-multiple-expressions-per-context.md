# [TICKET-002] Support Multiple Expressions Per Context (Within Same Time Range)

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Feature Addition

## Impact Assessment
**Business Impact:**
- 현재는 하나의 context time range에 하나의 expression만 추출 가능
- 여러 표현식이 같은 context에 존재할 수 있으나 놓치는 경우 발생
- 더 풍부한 교육 콘텐츠 생성 가능

**Technical Impact:**
- 영향받는 모듈: `langflix/core/models.py`, `langflix/core/expression_analyzer.py`, `langflix/templates/`, `langflix/main.py`, `langflix/core/video_editor.py`
- 예상 변경 파일: 8-12개
- 스키마 변경 필요 (data model)

**Effort Estimate:**
- Large (> 3 days)

## Problem Description

### Current State
**Location:** Multiple files

현재 시스템은 하나의 context time range에서 하나의 expression만 추출하도록 설계되어 있습니다:

**Prompt 제약** (`langflix/templates/expression_analysis_prompt_v2.txt:8`):
```
Find 1-3 expressions that English learners would be EXCITED to learn
```

하지만 LLM이 하나의 context에서 여러 expression을 추출할 수 있습니다 (예: 같은 대화에 2-3개의 유용한 표현식).

**문제:**
1. **Video extraction**: 같은 context에서 여러 expression을 추출하면 각각에 대해 동일한 context clip을 반복 생성 (비효율)
2. **Video build**: 각 expression이 독립적인 educational video를 생성 (중복)
3. **Data model**: 현재 `ExpressionAnalysis`가 single expression 모델
4. **Timing conflict**: 여러 expression이 같은 context_start_time/context_end_time 공유 시 충돌

### Root Cause Analysis
- 초기 설계가 single-expression-per-context 방식
- Prompt가 "1-3 expressions"라고 하더라도 실제 처리는 하나씩
- 비디오 처리 로직이 하나의 context에 하나의 video를 가정
- 데이터 모델이 independent expressions을 가정

### Evidence
- `langflix/templates/expression_analysis_prompt_v2.txt:8`: "Find 1-3 expressions" 명시
- `langflix/core/models.py:8-100`: `ExpressionAnalysis`가 single expression 모델
- `langflix/main.py:494-551`: 각 expression마다 독립적인 clip 생성
- `langflix/core/video_editor.py:106-198`: `create_educational_sequence`가 single expression만 받음

## Proposed Solution

### Approach
1. **Grouping Layer 추가**: 같은 context를 공유하는 expression들을 그룹화
2. **Shared Context Processing**: 같은 context의 expression들은 하나의 context clip 공유
3. **Multi-Expression Video Build**: 하나의 educational video에 여러 expression 포함 가능
4. **Data Model 확장**: Optional로 여러 expression을 하나의 context에 매핑
5. **Prompt 개선**: 명확히 "여러 expression 가능" 명시

### Implementation Details

#### Step 1: ADR 작성
`docs/adr/ADR-016-multiple-expressions-per-context.md` 생성:

```markdown
# ADR-016: Multiple Expressions Per Context Support

## Status
Proposed

## Context

현재 LangFlix는 하나의 context time range에서 하나의 expression만 추출합니다.
하지만 하나의 대화/장면에서 여러 유용한 표현식이 나올 수 있습니다.

예시:
- "I'll knock it out of the park for you" (context: 00:05:30 - 00:06:10)
  → Expression 1: "knock it out of the park" (00:05:35 - 00:05:45)
  → Expression 2: "for you" (00:05:40 - 00:05:42) - less valuable, skip
  → 하지만 두 표현식이 더 유용하면 둘 다 추출 가능

## Decision

동일한 context time range를 공유하는 여러 expression을 지원하도록 시스템 확장:
1. Expression grouping: 같은 context_start_time/context_end_time 공유
2. Shared context clip: 같은 context의 expression들은 하나의 video clip 공유
3. Educational video options:
   - Option A: 각 expression마다 독립적인 video (현재 방식 유지)
   - Option B: 하나의 video에 여러 expression 포함 (새로운 방식)
   - Option C: Configurable (기본값: Option A, 설정으로 Option B)

## Implementation Strategy

### Phase 1: Grouping & Data Model
- Expression grouping logic 추가
- Data structure로 grouped expressions 표현
- Backward compatibility 유지

### Phase 2: Video Processing
- Shared context clip reuse
- Multi-expression video generation

### Phase 3: Configuration & Optimization
- Configurable video generation modes
- Performance optimization

## Consequences

### Benefits
- 더 풍부한 콘텐츠
- 비디오 처리 효율 (중복 clip 제거)
- 더 유연한 추출

### Drawbacks
- 복잡도 증가
- 비디오 편집 로직 복잡화
- 테스트 시나리오 증가

## References
- TICKET-002
```

#### Step 2: ExpressionGroup 모델 추가
`langflix/core/models.py`에 추가:

```python
from typing import List
from pydantic import BaseModel, Field

class ExpressionGroup(BaseModel):
    """
    Groups multiple expressions that share the same context time range
    """
    context_start_time: str = Field(
        description="Shared context start time",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    context_end_time: str = Field(
        description="Shared context end time",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    expressions: List[ExpressionAnalysis] = Field(
        description="List of expressions in this context",
        min_length=1
    )
    
    @validator('expressions')
    def validate_single_context(cls, v):
        """Validate all expressions share same context times"""
        if not v:
            return v
        
        first_context_start = v[0].context_start_time
        first_context_end = v[0].context_end_time
        
        for expr in v[1:]:
            if expr.context_start_time != first_context_start or expr.context_end_time != first_context_end:
                raise ValueError("All expressions in group must share same context times")
        
        return v
```

#### Step 3: Expression Grouping Logic
`langflix/core/expression_analyzer.py`에 추가:

```python
from langflix.core.models import ExpressionAnalysis, ExpressionGroup

def group_expressions_by_context(expressions: List[ExpressionAnalysis]) -> List[ExpressionGroup]:
    """
    Group expressions that share the same context time range
    
    Args:
        expressions: List of expression analyses
        
    Returns:
        List of expression groups
    """
    groups: Dict[str, ExpressionGroup] = {}
    
    for expr in expressions:
        # Create unique key from context times
        context_key = f"{expr.context_start_time}_{expr.context_end_time}"
        
        if context_key in groups:
            groups[context_key].expressions.append(expr)
        else:
            groups[context_key] = ExpressionGroup(
                context_start_time=expr.context_start_time,
                context_end_time=expr.context_end_time,
                expressions=[expr]
            )
    
    return list(groups.values())
```

#### Step 4: LangFlixPipeline에 Grouping 통합
`langflix/main.py` 수정:

```python
from langflix.core.expression_analyzer import group_expressions_by_context

class LangFlixPipeline:
    def __init__(self, ..., enable_expression_grouping: bool = True):
        self.enable_expression_grouping = enable_expression_grouping
    
    def run(self, ...):
        # After analyzing expressions
        self.expressions = self._analyze_expressions(...)
        
        # Optionally group expressions by context
        if self.enable_expression_grouping and len(self.expressions) > 1:
            logger.info("Grouping expressions by shared context...")
            self.expression_groups = group_expressions_by_context(self.expressions)
            logger.info(f"Created {len(self.expression_groups)} expression groups")
            logger.info(f"  - {sum(1 for g in self.expression_groups if len(g.expressions) == 1)} single-expression groups")
            logger.info(f"  - {sum(1 for g in self.expression_groups if len(g.expressions) > 1)} multi-expression groups")
        else:
            # Create single-expression groups for compatibility
            self.expression_groups = [
                ExpressionGroup(
                    context_start_time=expr.context_start_time,
                    context_end_time=expr.context_end_time,
                    expressions=[expr]
                )
                for expr in self.expressions
            ]
```

#### Step 5: Video Processing 로직 수정
`langflix/main.py`의 `_process_expressions` 변경:

```python
def _process_expressions(self):
    """Process each expression group (video + subtitles)"""
    for group_idx, expression_group in enumerate(self.expression_groups):
        try:
            logger.info(f"Processing expression group {group_idx+1}/{len(self.expression_groups)}: {len(expression_group.expressions)} expressions")
            
            # Find video file
            video_file = self.video_processor.find_video_file(str(self.subtitle_file))
            if not video_file:
                logger.warning(f"No video file found for expression group {group_idx+1}")
                continue
            
            # Create ONE context clip for the entire group (shared)
            safe_expression = "group_expression" if len(expression_group.expressions) > 1 else expression_group.expressions[0].expression
            safe_filename = self._sanitize_filename(safe_expression)
            
            temp_dir = Path(tempfile.gettempdir())
            video_output = temp_dir / f"temp_group_{group_idx+1:02d}_{safe_filename[:30]}.mkv"
            
            # Extract ONE context clip for all expressions in group
            success = self.video_processor.extract_clip(
                video_file,
                expression_group.context_start_time,
                expression_group.context_end_time,
                video_output
            )
            
            if not success:
                logger.warning(f"Failed to create context clip for expression group {group_idx+1}")
                continue
            
            logger.info(f"✅ Shared context clip created: {video_output}")
            
            # Create subtitle files for EACH expression in the group
            for expr_idx, expression in enumerate(expression_group.expressions):
                subtitle_output = self.paths['language']['subtitles'] / f"group_{group_idx+1}_expr_{expr_idx+1}_{safe_filename[:30]}.srt"
                subtitle_output.parent.mkdir(parents=True, exist_ok=True)
                
                subtitle_success = self.subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output)
                )
                
                if subtitle_success:
                    logger.info(f"✅ Subtitle file created: {subtitle_output}")
                    self.processed_expressions += 1
                else:
                    logger.warning(f"❌ Failed to create subtitle file: {subtitle_output}")
            
        except Exception as e:
            logger.error(f"Error processing expression group {group_idx+1}: {e}")
            continue
```

#### Step 6: VideoEditor에 Multi-Expression 지원 추가
`langflix/core/video_editor.py` 수정:

```python
def create_educational_sequence(
    self, 
    expression_group: ExpressionGroup,  # Changed from single expression
    context_video_path: str, 
    expression_video_path: str, 
    group_index: int = 0
) -> List[str]:
    """
    Create educational video sequences for expression group
    
    Args:
        expression_group: ExpressionGroup with one or more expressions
        context_video_path: Path to context video
        expression_video_path: Path to expression video
        group_index: Index of expression group (for voice alternation)
        
    Returns:
        List of paths to created educational videos
    """
    from langflix import settings
    video_mode = settings.get_educational_video_mode()
    
    if video_mode == "separate" or len(expression_group.expressions) == 1:
        # Create separate video for each expression (current behavior)
        videos = []
        for expr_idx, expression in enumerate(expression_group.expressions):
            video_path = self._create_single_expression_video(
                expression, context_video_path, expression_video_path, 
                expression_index=group_index * 100 + expr_idx
            )
            videos.append(video_path)
        return videos
    
    elif video_mode == "combined":
        # Create one video with all expressions in the group
        return [self._create_multi_expression_video(
            expression_group, context_video_path, expression_video_path, group_index
        )]
    else:
        raise ValueError(f"Unknown video mode: {video_mode}")

def _create_multi_expression_video(
    self,
    expression_group: ExpressionGroup,
    context_video_path: str,
    expression_video_path: str,
    group_index: int
) -> str:
    """
    Create one educational video containing multiple expressions from same context
    
    Layout: Context → Expression1(repeat) → Expression2(repeat) → ...
    Right side: Combined slide showing all expressions
    """
    # Implementation for combined multi-expression video
    pass
```

#### Step 7: Configuration 추가
`langflix/config/default.yaml`:

```yaml
expression:
  llm:
    # Multiple expressions per context configuration
    max_expressions_per_context: 3  # Maximum expressions per context
    allow_multiple_expressions: true  # Enable/disable feature
  
  # Educational video generation mode
  educational_video_mode: "separate"  # "separate" (one per expression) or "combined" (one per group)
  
  # Playback configuration
  playback:
    expression_repeat_count: 2
    context_play_count: 1
    repeat_delay_ms: 200
```

#### Step 8: Prompt 업데이트
`langflix/templates/expression_analysis_prompt_v4.txt` 수정:

```
**YOUR MISSION:**
Find 1-3 expressions that English learners would be EXCITED to learn - expressions they'd actually use and remember.

**IMPORTANT:** You can extract MULTIPLE expressions from the SAME context if they are all valuable and teachable.
If you find 2-3 excellent expressions in one dialogue segment, include ALL of them.

**However:** Only extract multiple expressions from one context if:
- ALL expressions are valuable and reusable
- ALL expressions are clearly teachable
- The context has enough richness for multiple expressions

**If unsure:** Extract only the BEST single expression.

**MULTIPLE EXPRESSIONS EXAMPLE:**
Context: "I'll knock it out of the park for you, and you can count on it."
Expressions:
  1. "knock it out of the park" (main expression)
  2. "count on it" (secondary valuable expression)
  
Both can be extracted if both are valuable for learning.
```

### Alternative Approaches Considered

**Option 1: 항상 여러 expression 허용**
- 장점: 단순함
- 단점: 불필요한 expression 추출 가능
- 선택하지 않은 이유: 품질 관리 어려움

**Option 2: 선택된 접근 (Configurable with grouping)**
- 장점: 유연성, backward compatibility, 품질 제어
- 단점: 복잡도 증가
- 선택 이유: 최적 균형

**Option 3: 하나의 context에 무조건 하나만**
- 장점: 현 구조 유지
- 단점: 유용 표현 누락
- 선택하지 않은 이유: 기능 제한

### Benefits
- **풍부한 콘텐츠**
- **비디오 처리 효율**: 중복 clip 제거로 스토리지와 처리 절감
- **유연성**: 설정으로 모드 전환
- **하위 호환성**: 기본값으로 단일 expression 모드 유지
- **재사용성**: 하나의 context clip을 여러 expression에 활용

### Risks & Considerations
- **Breaking Changes**: 모델 변경에 따른 마이그레이션 필요
- **Video Build 복잡도**: multi-expression 시나리오 대응 로직 추가
- **Testing Complexity**: 단일/다중 조합 시나리오 증가
- **UI/UX**: 다중 모드에 따른 사용자 교육 필요

## Testing Strategy

### Unit Tests
- `group_expressions_by_context`: 그룹화 로직 검증
- `ExpressionGroup` 검증
- `_create_multi_expression_video`: 비디오 빌드 검증

### Integration Tests
- 단일/다중 context 처리 검증
- 그룹화 결과 검증
- 비디오 생성 품질 검증

### Performance Tests
- 단일 vs 다중 expression 처리 시간
- 스토리지 사용량 비교

## Files Affected

**새로 생성:**
- `docs/adr/ADR-016-multiple-expressions-per-context.md` - 아키텍처 결정
- `langflix/core/expression_grouper.py` - 그룹화 로직 (선택)

**수정:**
- `langflix/core/models.py` - `ExpressionGroup` 모델 추가
- `langflix/core/expression_analyzer.py` - 그룹화 함수 추가
- `langflix/main.py` - 그룹 처리 로직 추가
- `langflix/core/video_editor.py` - 다중 expression 비디오 생성
- `langflix/templates/expression_analysis_prompt_v4.txt` - 프롬프트 개선
- `langflix/config/default.yaml` - 설정 추가
- `langflix/settings.py` - 설정 접근자 추가

**테스트 추가:**
- `tests/unit/test_expression_grouping.py` - 그룹화 테스트
- `tests/integration/test_multi_expression_processing.py` - 통합 테스트
- `tests/performance/test_multi_vs_single.py` - 성능 테스트

## Dependencies
- Depends on: TICKET-001 (병렬 LLM 처리, 다중 expression 생성 속도 개선)
- Blocks: None
- Related to: ADR-016

## References
- Related code: `langflix/core/models.py`, `langflix/core/expression_analyzer.py`
- Prompt template: `langflix/templates/expression_analysis_prompt_v4.txt`
- Design patterns: Grouping Pattern, Strategy Pattern

## Architect Review Questions
**For the architect to consider:**
1. combined mode의 출력 형식
2. UI에서 그룹 표시 방식
3. backward compatibility 전략
4. 기본 동작: separate vs combined

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED (with architectural considerations)

**Strategic Rationale:**
- Enhances content richness - extracts more educational value from same context
- Improves efficiency - reduces duplicate video processing for shared contexts
- Aligns with prompt design - already asks for "1-3 expressions"
- High value feature - better user experience with richer content
- However: High complexity - requires data model changes, video processing refactoring

**Implementation Phase:** Phase 2 - Sprint 2 (Weeks 3-4)
**Sequence Order:** #2 in implementation queue (after TICKET-001 for performance foundation)

**Architectural Guidance:**

**Critical Architectural Decisions:**

1. **Data Model Strategy:**
   - **Option A (Recommended)**: Add `ExpressionGroup` as optional wrapper
     - Maintains backward compatibility (single expressions = group of 1)
     - Doesn't break existing code
     - Easier migration path
   - **Option B**: Change `ExpressionAnalysis` to support lists
     - Breaks backward compatibility
     - Requires extensive refactoring
     - **Rejected** - too disruptive

2. **Video Processing Strategy:**
   - **Separate mode (default)**: Create individual videos per expression
     - Maintains current UX
     - Easier to understand and navigate
     - No breaking changes
   - **Combined mode (optional)**: Single video with multiple expressions
     - Requires new video editing logic
     - More complex subtitle/audio handling
     - **Phase 2** - implement after separate mode proven

3. **Prompt Strategy:**
   - Current prompt already asks for "1-3 expressions"
   - LLM can already return multiple - system just needs to handle them
   - **No prompt changes needed initially** - just enable multi-expression handling

4. **Grouping Logic:**
   - Group by exact `context_start_time` and `context_end_time` match
   - Consider small tolerance (< 0.5s) for floating-point differences?
   - **Recommendation**: Exact match only initially, add tolerance if needed

5. **Video Clip Reuse:**
   - Same context = same video clip (critical efficiency gain)
   - Cache clips by context key to avoid duplicate extraction
   - **Important**: Track which clips are shared vs dedicated

6. **Timing Conflicts:**
   - Multiple expressions can have overlapping `expression_start_time/expression_end_time`
   - This is expected and OK - they're within the same context
   - Don't treat as errors

**Dependencies:**
- **Must complete first:** TICKET-001 (parallel processing helps with larger expression sets)
- **Should complete first:** None
- **Blocks:** None (backward compatible)
- **Related work:** ADR-016 (if creating new ADR for this feature)

**Risk Mitigation:**
- Risk: Breaking existing single-expression workflows
  - Mitigation: Default to separate mode, single expressions = groups of 1
  - Backward compatibility: Existing code works unchanged
- Risk: Video processing complexity
  - Mitigation: Start with separate mode only, add combined mode later
  - Test thoroughly with various expression counts
- Risk: Data migration
  - Mitigation: New feature - no migration needed, old data works as-is
- Risk: UI complexity
  - Mitigation: Separate mode maintains current UX, combined mode optional
- **Rollback strategy:** Feature flag - disable grouping, falls back to single-expression mode

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] ADR-016 created documenting architectural decisions
- [ ] ExpressionGroup model with validation
- [ ] Grouping logic handles edge cases (empty groups, timing mismatches)
- [ ] Separate mode fully working (backward compatible)
- [ ] Combined mode optional (can be Phase 2)
- [ ] Video clip caching/reuse verified (no duplicate extractions)
- [ ] Integration tests with 1, 2, 3+ expressions per context
- [ ] Backward compatibility tests (old single-expression workflows)
- [ ] Performance acceptable (no degradation vs single-expression)

**Alternative Approaches Considered:**
- Original proposal: ExpressionGroup with separate/combined modes ✅ Selected (balanced approach)
- Alternative 1: Always combine - Rejected (too complex, breaks UX)
- Alternative 2: Always separate - Rejected (misses efficiency gains)
- **Selected approach:** ExpressionGroup with separate mode default, combined optional - best balance

**Implementation Notes:**
- Start by: Creating ExpressionGroup model and grouping logic
- Watch out for: Timing precision issues (floating point comparison)
- Coordinate with: TICKET-001 team (parallel processing helps with larger expression sets)
- Reference: `langflix/core/models.py` for ExpressionAnalysis structure, `langflix/core/video_editor.py` for video creation logic

**Phased Implementation Recommendation:**
- **Phase 1**: ExpressionGroup model + grouping logic + separate mode (backward compatible)
- **Phase 2**: Combined mode + multi-expression video editing (new feature)
- **Phase 3**: UI enhancements for group display (if needed)

**Estimated Timeline:** 4-5 days (separate mode) + 3-4 days (combined mode) = 7-9 days total
**Recommended Owner:** Senior engineer (complex data model and video processing changes)

## Success Criteria
How do we know this is successfully implemented?
- [ ] 같은 context의 여러 expression 추출 지원
- [ ] ExpressionGroup 모델 동작 검증
- [ ] Shared context clip 재사용
- [ ] Separate/combined 모드 정상 동작
- [ ] 기존 단일 expression 처리 유지
- [ ] 충분한 테스트 커버리지
- [ ] 문서 업데이트 완료

