# [TICKET-013] Fix Multiple Expression Video Processing Bugs

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- 두 번째 이상의 표현식 비디오가 시작 부분에서 프리즈되어 사용자 경험 저하
- 첫 번째 컨텍스트 비디오 자막이 잘못되어 학습 효과 저하
- 임시 파일이 누적되어 디스크 공간 부족 문제 발생 가능

**Technical Impact:**
- 영향받는 모듈: `langflix/core/video_editor.py`, `langflix/main.py`
- 예상 변경 파일: 2-3개
- Breaking changes: 없음 (버그 수정)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Bug 1: Second Expression Video Freezes at Beginning

**Location:** `langflix/core/video_editor.py:136-178`, `langflix/main.py:827-833`

**Symptoms:**
- 두 번째 표현식 비디오가 시작 부분에서 프리즈됨
- 비디오가 처음 몇 초간 멈춘 상태로 시작
- 이전에 유사한 문제가 있었고 시작/종료 시간 설정 오류로 해결된 경험

**Current State:**
```python
# langflix/core/video_editor.py:136-178
def create_educational_sequence(self, expression: ExpressionAnalysis, 
                                  context_video_path: str, 
                                  expression_video_path: str, 
                                  expression_index: int = 0,
                                  skip_context: bool = False) -> str:
    # Calculate relative timestamps within context video
    context_start_seconds = self._time_to_seconds(expression.context_start_time)
    expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
    expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
    
    relative_start = expression_start_seconds - context_start_seconds
    relative_end = expression_end_seconds - context_start_seconds
    expression_duration = relative_end - relative_start
    
    # Extract expression clip from context
    input_stream = ffmpeg.input(str(context_with_subtitles), ss=relative_start, t=expression_duration)
    video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
    audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')
```

**Root Cause Analysis:**
- Multi-expression 그룹에서 여러 표현식이 같은 `context_video_path`를 공유
- 각 표현식의 `expression_start_time`과 `expression_end_time`이 컨텍스트 비디오 내 상대 시간으로 올바르게 계산되어야 함
- 하지만 `relative_start` 계산 시 `expression_start_time`이 절대 시간인지 상대 시간인지 명확하지 않음
- `setpts` 필터를 사용하지만 타임스탬프 리셋이 제대로 되지 않아 프리즈 발생 가능

**Evidence:**
- `output/Suits/Suits.S01E01.720p.HDTV.x264/translations/ko/long_form_videos/` 디렉토리에 `temp_expr_clip_long_*.mkv` 파일들이 있음
- 사용자 보고: "second expression video freeze in the beginning, we saw similar issue before comes from start/end time set wrong"

### Bug 2: First Context Video Subtitles Are Wrong

**Location:** `langflix/main.py:796-798`, `langflix/core/video_editor.py:490-527`

**Symptoms:**
- 첫 번째 컨텍스트 비디오 자막이 완전히 잘못됨
- 매우 첫 번째 자막만 표시되고 업데이트되지 않음
- Multi-expression 그룹에서 첫 번째 표현식의 자막이 모든 표현식에 적용됨

**Current State:**
```python
# langflix/main.py:796-798
# Add subtitles to context video first
context_with_subtitles = self.video_editor._add_subtitles_to_context(
    str(context_video), expression_group.expressions[0]  # Use first expression for subtitle context
)
```

```python
# langflix/core/video_editor.py:490-527
def _add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis) -> str:
    safe_name = sanitize_for_expression_filename(expression.expression)
    output_path = context_videos_dir / f"context_{safe_name}.mkv"
    
    # Check if file already exists (created by long-form)
    if output_path.exists():
        logger.info(f"Reusing existing context_with_subtitles: {output_path.name}")
        return str(output_path)  # ← 문제: 다른 표현식이 재사용하면서 첫 번째 표현식 자막만 표시
```

**Root Cause Analysis:**
1. Multi-expression 그룹에서 첫 번째 표현식만 사용하여 자막 추가 (`expression_group.expressions[0]`)
2. `_add_subtitles_to_context`가 표현식 이름으로 파일 경로를 생성 (`context_{safe_name}.mkv`)
3. 같은 컨텍스트 비디오에 여러 표현식이 있을 때, 첫 번째 표현식으로 생성된 자막 파일이 재사용됨
4. 하지만 실제로는 각 표현식마다 다른 자막이 필요한데, 파일 이름이 표현식별로 다르므로 첫 번째 표현식의 자막만 사용됨
5. Multi-expression 그룹의 경우, 컨텍스트 비디오는 하나이지만 각 표현식마다 다른 자막이 필요함

**Evidence:**
- 사용자 보고: "when first context video subtitle is completely wrong it has very first subtitle, but then doesn't get updated"
- `_add_subtitles_to_context`가 표현식 이름으로 파일을 생성하므로, 같은 컨텍스트에 여러 표현식이 있을 때 충돌

### Bug 3: Temporary Files Not Cleaned Up in long_form_videos Directory

**Location:** `langflix/core/video_editor.py:155-217`, `langflix/main.py:873-884`

**Symptoms:**
- `long_form_videos` 디렉토리의 모든 임시 파일(`temp_*`)이 삭제되지 않음
- 디스크 공간 누적 사용
- 수동으로 정리해야 함

**Current State:**
```python
# langflix/main.py:873-884
# Clean up temp video clips after processing using temp manager
logger.info("Cleaning up temporary video clips...")
for video_file in group_video_files:  # ← group_video_files만 정리
    try:
        if video_file.exists():
            if Path(video_file) in temp_manager.temp_files:
                temp_manager.temp_files.remove(Path(video_file))
            Path(video_file).unlink()
```

```python
# langflix/core/video_editor.py:155-217
# 임시 파일들이 output_dir (long_form_videos)에 생성됨
expression_video_clip_path = self.output_dir / f"temp_expr_clip_long_{safe_expression}.mkv"
self._register_temp_file(expression_video_clip_path)  # ← TempFileManager에 등록

repeated_expression_path = self.output_dir / f"temp_expr_repeated_{safe_expression}.mkv"
self._register_temp_file(repeated_expression_path)

left_side_path = self.output_dir / f"temp_left_side_long_{safe_expression}.mkv"
self._register_temp_file(left_side_path)

hstack_temp_path = self.output_dir / f"temp_hstack_long_{safe_expression}.mkv"
self._register_temp_file(hstack_temp_path)
```

**Root Cause Analysis:**
1. `VideoEditor`의 `output_dir`가 `long_form_videos` 디렉토리로 설정됨 (`langflix/main.py:225`)
2. 임시 파일들이 `output_dir`에 생성되고 `_register_temp_file`로 등록됨
3. 하지만 `_cleanup_temp_files()`가 호출되지 않거나, 호출되어도 `long_form_videos` 디렉토리의 임시 파일이 정리되지 않음
4. `_create_educational_videos()`에서 `group_video_files`만 정리하고, `VideoEditor`에서 생성한 다른 임시 파일들은 정리하지 않음
5. `_cleanup_resources()`에서 `video_editor._cleanup_temp_files()`를 호출하지만, 이미 사용 중인 파일이 있을 수 있음

**Evidence:**
- `output/Suits/Suits.S01E01.720p.HDTV.x264/translations/ko/long_form_videos/` 디렉토리에 많은 `temp_*` 파일들이 남아있음:
  - `temp_vstack_short_*.mkv`
  - `temp_slide_silent_*.mkv`
  - `temp_concatenated_av_*.mkv`
  - `temp_hstack_long_*.mkv`
  - `temp_slide_*.mkv`
  - `temp_expr_repeated_*.mkv`
  - `temp_expr_clip_long_*.mkv`
  - `temp_context_multi_hstack_*.mkv`
  - `temp_multi_slide_*.mkv`
- 사용자 보고: "all temporary files are not getting deleted"

## Proposed Solution

### Bug 1 Fix: Correct Expression Timestamp Calculation

**Approach:**
1. `expression_start_time`과 `expression_end_time`이 컨텍스트 비디오 내 상대 시간인지 확인
2. 타임스탬프 리셋을 더 확실하게 처리
3. `setpts` 필터와 함께 `-ss` 옵션 정확도 개선

**Implementation:**
```python
# langflix/core/video_editor.py:136-178
def create_educational_sequence(self, expression: ExpressionAnalysis, 
                                  context_video_path: str, 
                                  expression_video_path: str, 
                                  expression_index: int = 0,
                                  skip_context: bool = False) -> str:
    # Calculate relative timestamps within context video
    context_start_seconds = self._time_to_seconds(expression.context_start_time)
    expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
    expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
    
    # Ensure expression times are within context range
    if expression_start_seconds < context_start_seconds:
        logger.warning(f"Expression start time {expression.expression_start_time} is before context start {expression.context_start_time}")
        expression_start_seconds = context_start_seconds
    
    relative_start = expression_start_seconds - context_start_seconds
    relative_end = expression_end_seconds - context_start_seconds
    expression_duration = relative_end - relative_start
    
    # Ensure non-negative duration
    if expression_duration <= 0:
        logger.error(f"Invalid expression duration: {expression_duration:.2f}s")
        raise ValueError(f"Expression duration must be positive, got {expression_duration:.2f}s")
    
    logger.info(f"Expression relative: {relative_start:.2f}s - {relative_end:.2f}s ({expression_duration:.2f}s)")
    
    # Extract expression clip from context with proper timestamp handling
    # Use both -ss and setpts to ensure timestamps are reset correctly
    expression_video_clip_path = self.output_dir / f"temp_expr_clip_long_{safe_expression}.mkv"
    self._register_temp_file(expression_video_clip_path)
    
    # Extract with -ss for seeking, then reset timestamps
    input_stream = ffmpeg.input(str(context_with_subtitles), ss=relative_start, t=expression_duration)
    # Reset PTS to start from 0 for both video and audio
    video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
    audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')
    
    # Use fast seek for better accuracy
    (
        ffmpeg.output(
            video_stream,
            audio_stream,
            str(expression_video_clip_path),
            vcodec='libx264',
            acodec='aac',
            ac=2,
            ar=48000,
            preset='fast',
            crf=23,
            **{'-avoid_negative_ts': 'make_zero'}  # Ensure timestamps start from 0
        )
        .overwrite_output()
        .run(quiet=True)
    )
```

### Bug 2 Fix: Use Group-Specific Subtitle Context for Multi-Expression Groups

**Approach:**
1. Multi-expression 그룹의 경우, 컨텍스트 비디오 자막 파일을 그룹별로 생성
2. 각 표현식이 올바른 자막을 사용하도록 수정
3. 자막 파일 이름을 표현식별이 아닌 그룹별로 생성하거나, 각 표현식마다 올바른 자막 생성

**Implementation:**
```python
# langflix/main.py:796-798 수정
if is_multi_expression:
    # Multi-expression group: Create context video with multi-expression slide FIRST
    try:
        logger.info(
            f"Creating context video with multi-expression slide for group {group_idx+1} "
            f"({len(expression_group.expressions)} expressions)"
        )
        
        # For multi-expression groups, use a group-specific context subtitle file
        # Create context video with subtitles for the group (use first expression's subtitle as base)
        context_with_subtitles = self.video_editor._add_subtitles_to_context(
            str(context_video), 
            expression_group.expressions[0],  # Use first expression for subtitle context
            group_id=f"group_{group_idx+1:02d}"  # Pass group ID for unique filename
        )
        
        # Create context video with multi-expression slide
        context_video_with_slide = self.video_editor.create_context_video_with_multi_slide(
            context_with_subtitles,
            expression_group
        )
        
        educational_videos.append(context_video_with_slide)
        logger.info(f"✅ Context video with multi-expression slide created: {context_video_with_slide}")
```

```python
# langflix/core/video_editor.py:490-527 수정
def _add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis, group_id: Optional[str] = None) -> str:
    """Add target language subtitles to context video (translation only) using overlay helpers."""
    try:
        context_videos_dir = self.output_dir.parent / "context_videos"
        context_videos_dir.mkdir(exist_ok=True)

        safe_name = sanitize_for_expression_filename(expression.expression)
        # Use group_id for multi-expression groups to create unique filename
        if group_id:
            output_path = context_videos_dir / f"context_{group_id}.mkv"
        else:
            output_path = context_videos_dir / f"context_{safe_name}.mkv"
        
        # Check if file already exists (created by long-form)
        if output_path.exists():
            logger.info(f"Reusing existing context_with_subtitles: {output_path.name}")
            return str(output_path)

        subtitle_dir = self.output_dir.parent / "subtitles"
        sub_path = subs_overlay.find_subtitle_file(subtitle_dir, expression.expression)

        if sub_path and Path(sub_path).exists():
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_sub_name = f"temp_dual_lang_{group_id or safe_name}.srt"
            temp_sub = temp_dir / temp_sub_name
            self._register_temp_file(temp_sub)
            subs_overlay.create_dual_language_copy(Path(sub_path), temp_sub)
            subs_overlay.apply_subtitles_with_file(Path(video_path), temp_sub, output_path, is_expression=False)
        else:
            # drawtext fallback with translation only
            translation_text = ""
            if expression.translation and len(expression.translation) > 0:
                translation_text = expression.translation[0]
            else:
                translation_text = expression.expression_translation
            subs_overlay.drawtext_fallback_single_line(Path(video_path), translation_text, output_path)

        return str(output_path)

    except Exception as e:
        logger.error(f"Error adding subtitles to context: {e}")
        raise
```

그리고 각 표현식의 educational video 생성 시에도 올바른 자막 사용:
```python
# langflix/core/video_editor.py:148-151 수정
# Get context video with subtitles for THIS expression (not first expression in group)
context_with_subtitles = self._add_subtitles_to_context(
    context_video_path, expression  # Use current expression, not first in group
)
```

### Bug 3 Fix: Clean Up All Temporary Files in long_form_videos Directory

**Approach:**
1. `_create_educational_videos()` 완료 후 모든 임시 파일 정리
2. `VideoEditor`의 `_cleanup_temp_files()` 명시적으로 호출
3. `long_form_videos` 디렉토리의 `temp_*` 파일들 패턴 매칭으로 정리

**Implementation:**
```python
# langflix/main.py:873-884 수정
# Clean up temp video clips after processing using temp manager
logger.info("Cleaning up temporary video clips...")
for video_file in group_video_files:
    try:
        if video_file.exists():
            # Remove from manager's tracking if registered
            if Path(video_file) in temp_manager.temp_files:
                temp_manager.temp_files.remove(Path(video_file))
            Path(video_file).unlink()
            logger.debug(f"Deleted temp file: {video_file}")
    except Exception as e:
        logger.warning(f"Could not delete temp file {video_file}: {e}")

# Clean up all temporary files created by VideoEditor
logger.info("Cleaning up VideoEditor temporary files...")
if hasattr(self, 'video_editor'):
    try:
        # Clean up registered temp files
        self.video_editor._cleanup_temp_files()
        
        # Also clean up any remaining temp_* files in long_form_videos directory
        final_videos_dir = self.paths['language']['final_videos']
        temp_files_pattern = list(final_videos_dir.glob("temp_*.mkv"))
        temp_files_pattern.extend(list(final_videos_dir.glob("temp_*.txt")))
        temp_files_pattern.extend(list(final_videos_dir.glob("temp_*.wav")))
        
        for temp_file in temp_files_pattern:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Deleted leftover temp file: {temp_file.name}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")
        
        logger.info(f"✅ Cleaned up {len(temp_files_pattern)} temporary files")
    except Exception as e:
        logger.warning(f"Failed to cleanup VideoEditor temporary files: {e}")
```

또는 더 나은 방법으로, `VideoEditor`의 `_cleanup_temp_files()`를 개선:
```python
# langflix/core/video_editor.py:474-488 수정
def _cleanup_temp_files(self) -> None:
    """Clean up all temporary files created by this VideoEditor instance."""
    try:
        # Clean up files registered via _register_temp_file
        if hasattr(self, 'temp_manager'):
            self.temp_manager.cleanup_all()
        
        # Also clean up any temp_* files in output_dir (long_form_videos)
        if hasattr(self, 'output_dir') and self.output_dir.exists():
            temp_files = list(self.output_dir.glob("temp_*.mkv"))
            temp_files.extend(list(self.output_dir.glob("temp_*.txt")))
            temp_files.extend(list(self.output_dir.glob("temp_*.wav")))
            
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        logger.debug(f"Cleaned up temp file: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
            
            logger.info(f"✅ Cleaned up {len(temp_files)} temporary files from {self.output_dir}")
    except Exception as e:
        logger.warning(f"Error during temp file cleanup: {e}")
```

### Alternative Approaches Considered
- **Bug 1**: FFmpeg의 `-ss` 옵션 위치 변경 (input 전/후) - Rejected (현재 위치가 더 정확)
- **Bug 2**: 각 표현식마다 별도 컨텍스트 비디오 생성 - Rejected (비효율적, 공유 목적 상실)
- **Bug 3**: 모든 임시 파일을 별도 temp 디렉토리에 생성 - Rejected (기존 구조 유지가 나음)

### Benefits
- **Bug 1**: 두 번째 이상의 표현식 비디오가 정상 재생
- **Bug 2**: 각 표현식에 올바른 자막 표시
- **Bug 3**: 디스크 공간 절약, 수동 정리 불필요

### Risks & Considerations
- **Breaking changes**: 없음 (버그 수정)
- **성능**: 임시 파일 정리로 인한 처리 시간 증가 미미
- **호환성**: 기존 생성된 비디오 파일에 영향 없음

## Testing Strategy
- **Unit Tests**:
  - Expression timestamp 계산 테스트
  - 자막 파일 생성 및 재사용 테스트
  - 임시 파일 정리 테스트
- **Integration Tests**:
  - Multi-expression 그룹 전체 워크플로우 테스트
  - 두 번째 표현식 비디오 정상 재생 확인
  - 각 표현식의 올바른 자막 표시 확인
  - 임시 파일 정리 확인
- **Manual Testing**:
  - 실제 비디오 생성 후 확인
  - `long_form_videos` 디렉토리 정리 확인

## Files Affected
- `langflix/core/video_editor.py` - `create_educational_sequence()`, `_add_subtitles_to_context()`, `_cleanup_temp_files()` 수정
- `langflix/main.py` - `_create_educational_videos()` 수정 (자막 생성 및 정리)
- `tests/integration/test_multiple_expressions_per_context.py` - 버그 수정 테스트 추가
- `tests/unit/test_video_editor.py` - 단위 테스트 추가

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-008 (Multiple expressions per context)

## References
- Related documentation: `docs/adr/ADR-016-multiple-expressions-per-context.md`
- Related ticket: `tickets/done/TICKET-008-support-multiple-expressions-per-context.md`
- FFmpeg timestamp handling: https://ffmpeg.org/ffmpeg.html#Main-options

## Architect Review Questions
**For the architect to consider:**
1. Multi-expression 그룹의 자막 처리 전략: 그룹별로 하나의 자막 파일을 사용할 것인가, 각 표현식별로 별도 자막 파일을 사용할 것인가?
2. 임시 파일 정리 타이밍: 모든 비디오 생성 후 한 번에 정리할 것인가, 각 단계마다 정리할 것인가?
3. 타임스탬프 정확도: FFmpeg의 `-ss` 옵션과 `setpts` 필터 조합이 충분한가?

## Success Criteria
How do we know this is successfully implemented?
- [ ] 두 번째 이상의 표현식 비디오가 시작 부분에서 프리즈되지 않음
- [ ] 각 표현식의 컨텍스트 비디오에 올바른 자막이 표시됨
- [ ] `long_form_videos` 디렉토리의 모든 임시 파일이 자동으로 정리됨
- [ ] 모든 관련 테스트 통과
- [ ] 기존 기능에 영향 없음 (단일 표현식 그룹)
- [ ] 수동으로 임시 파일을 정리할 필요 없음

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- TICKET-008 (Multiple expressions per context) 구현 후 버그 수정
- 비디오 품질 이슈로 UX 영향 큼
- 디스크 공간 누수 위험
- TICKET-008 피쳐 품질 보장

**Implementation Phase:** Phase 1 - Sprint 1
**Sequence Order:** #4 (TICKET-008 완료 후 즉시)

**Architectural Guidance:**
- Multi-expression 그룹 자막: 그룹별 단일 자막 파일 사용. 컨텍스트 동일하므로 각 표현식 자막 불필요. 첫 표현식 자막 적용.
- 임시 파일 정리: 각 그룹 완료 후 즉시 정리. `temp_*` 패턴 매칭 추가.
- 타임스탬프: `-ss` + `setpts` + `avoid_negative_ts` 충분. 버퍼 0.2s 유지.

**Dependencies:**
- **Must complete first:** TICKET-008
- **Should complete first:** 없음
- **Blocks:** Multi-expression 안정성
- **Related work:** TICKET-008, TICKET-003 (temp file management)

**Risk Mitigation:**
- FFmpeg 복잡도: `avoid_negative_ts` 추가, 타임스탬프 검증.
- 자막 재사용: 그룹 ID 사용, 표현식/그룹 모드 분리.
- 임시 파일: 패턴 매칭 + `atexit`, 즉시 정리 옵션.

**Alternative Approaches Considered:**
- 각 표현식별 자막: 불필요한 중복과 충돌.
- 즉시 정리 vs 그룹 완료 후: 그룹 완료 후 정리 선택(디버깅 유리).
- **Selected approach:** group_id 자막, 패턴 매칭 정리, 타임스탬프 검증.

**Implementation Notes:**
- `_add_subtitles_to_context`에 `group_id` 추가. 단일 표현식은 expression 기반 이름 유지.
- `_cleanup_temp_files` 패턴 매칭 보강. `cleanup_all`에서 실행.
- `create_educational_sequence`에 타임스탬프 검증 추가.

**Estimated Timeline:** 2-3일
**Recommended Owner:** 중급+

---
