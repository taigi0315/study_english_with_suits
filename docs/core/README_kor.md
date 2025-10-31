# Core 모듈 문서

## 개요

`langflix/core/` 모듈은 LangFlix의 핵심 비디오 편집 기능을 포함합니다. 이 모듈은 long-form (side-by-side) 및 short-form (vertical) 비디오 레이아웃을 포함한 교육용 비디오 시퀀스 생성을 조율합니다.

**최종 업데이트:** 2025-01-30  
**관련 티켓:** TICKET-001

## 목적

이 모듈은 다음을 담당합니다:
- 컨텍스트 클립과 표현 반복이 포함된 교육용 비디오 시퀀스 생성
- side-by-side 레이아웃(hstack)을 가진 long-form 비디오 생성
- vertical 레이아웃(vstack)을 가진 short-form 비디오 생성
- 자막 오버레이 및 교육 슬라이드 관리
- 파이프라인 전체에서 오디오/비디오 동기화 조율

## 주요 구성 요소

### VideoEditor 클래스

비디오 생성을 조율하는 주요 클래스입니다.

**위치:** `langflix/core/video_editor.py`

**임시 파일 관리 (TICKET-002):**
- 모든 임시 파일 작업에 `TempFileManager` 사용
- 컨텍스트 관리자를 통해 임시 파일 자동 정리
- 수동 정리 불필요 - `TempFileManager`가 `atexit` 등록을 통해 처리
- 배치 생성 후 개별 short 비디오 파일 자동 정리

**주요 메서드:**

#### `create_educational_sequence()`
Side-by-side 레이아웃으로 long-form 교육용 비디오 시퀀스를 생성합니다:
- **왼쪽:** 컨텍스트 비디오 → 표현 반복 (자막 포함)
- **오른쪽:** 교육 슬라이드 (배경 + 텍스트 + 오디오)
- **레이아웃:** `hstack_keep_height()`를 사용한 수평 스택(hstack)
- **오디오:** AV 스트림에서만 (슬라이드 오디오 혼합 없음)

**워크플로우:**
1. 이중 언어 자막이 포함된 컨텍스트 비디오 생성
2. 컨텍스트 비디오에서 표현 클립 추출
3. `repeat_av_demuxer()`를 사용하여 표현 클립 반복 (안정성을 위한 demuxer 기반)
4. 컨텍스트 + 표현 반복 연결
5. 왼쪽 지속 시간과 일치하도록 확장된 교육 슬라이드 생성
6. 수평으로 스택 (hstack) - 왼쪽=AV, 오른쪽=slide
7. 별도 패스로 최종 오디오 gain (+25%) 적용

**파라미터:**
- `expression`: ExpressionAnalysis 객체
- `context_video_path`: 컨텍스트 비디오 경로
- `expression_video_path`: 표현 비디오 경로
- `expression_index`: 음성 교대용 인덱스

**반환값:** 생성된 교육용 비디오 경로

#### `create_short_format_video()`
Vertical 레이아웃으로 short-form 교육용 비디오 시퀀스를 생성합니다:
- **위쪽:** 연결된 컨텍스트 + 표현 세그먼트 (자막 포함)
- **아래쪽:** 교육 슬라이드 (전체 시간 동안 표시)
- **레이아웃:** `vstack_keep_width()`를 사용한 수직 스택(vstack)
- **오디오:** 연결된 비디오에서만 (vstack에 의해 보존됨)

**워크플로우 (TICKET-001 Phase 5에서 단순화됨):**
1. `context_with_subtitles` 생성 (long-form에서 존재하는 경우 재사용)
2. 표현 클립 추출 (long-form에서 존재하는 경우 재사용)
3. 표현 클립 반복 (long-form에서 존재하는 경우 재사용)
4. `concat_demuxer_if_uniform()`를 사용하여 컨텍스트 + 표현 세그먼트 연결 (복사 모드)
5. 비디오 지속 시간과 일치하도록 확장된 교육 슬라이드 생성
6. 수직으로 스택 (vstack) - 위쪽=AV, 아래쪽=slide
7. 별도 패스로 최종 오디오 gain (+25%) 적용

**주요 개선사항 (TICKET-001):**
- 불필요한 오디오 추출/처리 로직 약 180줄 제거
- long-form과 동일한 소스 비디오 사용 (`context_with_subtitles`)
- long-form의 중간 파일 재사용 (표현 클립, 반복 세그먼트)
- 비디오에서 지속 시간 계산 (오디오가 아님)
- 별도 오디오 처리 없음 - 오디오가 파이프라인 전체에서 비디오와 함께 유지됨

**파라미터:**
- `expressions`: ExpressionAnalysis 객체 목록
- `context_video_path`: 컨텍스트 비디오 경로
- `output_filename`: 출력 파일명

**반환값:** 생성된 short-form 비디오 경로

### 헬퍼 메서드

#### `_add_subtitles_to_context()`
컨텍스트 비디오에 이중 언어 자막을 추가합니다.

**개선사항 (TICKET-001 Phase 4):**
- 파일이 존재하는지 확인하고 재사용 (long-form과 short-form 간 충돌 방지)
- 일관된 자막 스타일링 사용

#### `_sanitize_filename()`
파일명 사용을 위해 표현 이름을 정리합니다.

**TICKET-001 Phase 4에 중요:**
- 정규식 사용: `re.sub(r'[^\w\s-]', '', text)` 그 다음 `re.sub(r'[-\s]+', '_', text)`
- 표현 일치를 보장하기 위해 `jobs.py` 정리와 정확히 일치해야 함

#### `_create_educational_slide()`
배경 이미지/텍스트 및 선택적 TTS 오디오가 있는 교육 슬라이드를 생성합니다.

**개선사항 (TICKET-001):**
- 선택적 `target_duration` 파라미터 허용
- 제공된 경우, 대상과 일치하도록 슬라이드 지속 시간 확장 (적절한 hstack/vstack 정렬용)

## 아키텍처 패턴

### Demuxer 우선 접근법 (TICKET-001)

모듈은 이제 최대 안정성을 위해 demuxer 기반 작업을 사용합니다:

1. **표현 반복:** `repeat_av_demuxer()` - filter concat 대신 concat demuxer 사용
2. **연결:** `concat_demuxer_if_uniform()` - 타임스탬프 보존을 위해 복사 모드 사용 (재인코딩 없음)
3. **Fallback:** demuxer 실패 시 filter concat으로 자동 fallback

**이점:**
- 오디오를 안정적으로 보존
- 타임스탬프 보존 (A-V 동기화 문제 없음)
- 더 간단한 파이프라인 그래프
- 더 나은 성능 (복사 모드)

### 파일 재사용 전략 (TICKET-001 Phase 3-4)

이제 long-form과 short-form 모두 중간 파일을 공유합니다:

1. **공유 표현 반복:** `temp_expr_repeated_{expression}.mkv`
   - long-form에 의해 생성됨
   - 존재하는 경우 short-form에서 재사용

2. **공유 표현 클립:** `temp_expr_clip_long_{expression}.mkv`
   - long-form에 의해 생성됨
   - 존재하는 경우 short-form에서 재사용

3. **공유 자막 포함 컨텍스트:** `context_with_subtitles`
   - 두 형식 모두에 의해 생성됨
   - 생성 전 확인 (존재하는 경우 재사용)

**이점:**
- 일관된 소스 자료
- 처리 시간 감소
- 충돌 또는 불일치 없음

### 관심사 분리

파이프라인은 명확한 분리를 따릅니다:

1. **AV 빌드:** 연결된 비디오 생성 (컨텍스트 + 표현 반복)
2. **레이아웃:** 슬라이드와 AV 스택 (long-form은 hstack, short-form은 vstack)
3. **최종 Gain:** 별도 패스로 오디오 gain (+25%) 적용

**이점:**
- 각 단계 테스트 용이
- 더 명확한 오류 처리
- 더 나은 유지보수성

## 종속성

### 내부 종속성
- `langflix/media/ffmpeg_utils.py` - FFmpeg 유틸리티
  - `repeat_av_demuxer()` - 표현 반복
  - `concat_demuxer_if_uniform()` - 연결
  - `concat_filter_with_explicit_map()` - Fallback 연결
  - `hstack_keep_height()` - Long-form 레이아웃
  - `vstack_keep_width()` - Short-form 레이아웃
  - `apply_final_audio_gain()` - 최종 오디오 부스트
  - `get_duration_seconds()` - 지속 시간 측정
- `langflix/subtitles/overlay.py` - 자막 오버레이 기능
- `langflix/slides/generator.py` - 교육 슬라이드 생성
- `langflix/config/` - 구성 관리

### 외부 종속성
- `ffmpeg-python` - FFmpeg Python 바인딩
- `pathlib` - 경로 조작
- 표준 라이브러리: `logging`, `os`, `re`

## 일반 작업

### 새 비디오 레이아웃 형식 추가

1. `langflix/media/ffmpeg_utils.py`에 새 스택 함수 생성 (예: `grid_keep_aspect()`)
2. `VideoEditor` 클래스에 새 메서드 추가 (예: `create_grid_format_video()`)
3. 동일한 패턴 따르기: AV 빌드 → 레이아웃 → 최종 gain
4. 공유 중간 파일로 파일 재사용 보장
5. `tests/integration/test_media_pipeline_*.py`에 테스트 추가

### 표현 반복 로직 수정

1. 반복 로직은 `langflix/media/ffmpeg_utils.py`에 중앙 집중화됨
2. `create_educational_sequence()`와 `create_short_format_video()` 모두 `repeat_av_demuxer()` 사용
3. 공유 파일명 형식 보장: `temp_expr_repeated_{sanitized_expression}.mkv`
4. 다른 표현 길이 및 카운트로 테스트

### A-V 동기화 문제 디버깅

1. **타임스탬프 보존 확인:**
   ```bash
   ffprobe -v error -show_entries stream=codec_time_base,input_time_base input.mkv
   ```

2. **복사 모드 사용 여부 확인:**
   - 로그에서 `vcodec=copy` 찾기 (demuxer concat)
   - 가능한 경우 재인코딩 피하기

3. **프레임 속도 일관성 확인:**
   - 모든 입력이 동일한 프레임 속도 사용 (filter concat에서 25fps로 정규화)

4. **검증 스크립트 실행:**
   ```bash
   python tools/verify_media_pipeline.py
   ```

## 주의사항 및 참고사항

### 표현 이름 정리

⚠️ **중요:** 표현 이름 정리는 다음 사이에서 정확히 일치해야 합니다:
- `langflix/core/video_editor.py::_sanitize_filename()`
- `langflix/api/routes/jobs.py` (작업 생성 시 정리)

**불일치 시 문제:** Short-form에서 첫 번째 표현 누락 (TICKET-001 이슈 3)

**해결책:** 두 위치에서 동일한 정규식 패턴 사용:
```python
sanitized = re.sub(r'[^\w\s-]', '', text)
sanitized = re.sub(r'[-\s]+', '_', sanitized)
```

### 파일 재사용 및 충돌

⚠️ **중요:** Long-form과 short-form 모두 `context_with_subtitles`를 생성합니다. 생성 전 항상 파일 존재 확인:

```python
if Path(context_with_subtitles).exists():
    logger.info(f"Reusing existing context_with_subtitles: {context_with_subtitles}")
else:
    # Create new file
```

### 오디오 처리 단순화

✅ **모범 사례:** TICKET-001 Phase 5 이후, short-form은 다음을 수행하지 않아야 합니다:
- 별도로 오디오 추출
- 별도로 오디오 처리
- 오디오에서 지속 시간 계산

✅ **해야 할 것:**
- 파이프라인 전체에서 비디오와 함께 오디오 유지
- 비디오에서 지속 시간 계산
- vstack 출력 직접 사용 (오디오가 이미 보존됨)

### Demuxer vs Filter Concat

**Demuxer concat 사용 시기:**
- 파라미터가 균일한 경우 (동일한 코덱, 해상도, 프레임 속도)
- 복사 모드 사용 원함 (재인코딩 없음, 타임스탬프 보존)
- 성능이 중요한 경우

**Filter concat 사용 시기:**
- 입력 간 파라미터가 다른 경우
- 프레임 속도 정규화 필요
- Demuxer concat이 실패하는 경우

**현재 전략:** 먼저 demuxer 시도, 자동으로 filter concat으로 fallback.

## 테스트

### 통합 테스트
- `tests/integration/test_media_pipeline_audio.py` - 파이프라인을 통한 오디오 보존
- `tests/functional/test_educational_video.py` - 종단 간 교육용 비디오 생성

### 검증 스크립트
- `tools/verify_media_pipeline.py` - ffprobe 체크를 포함한 포괄적인 파이프라인 검증

## 관련 문서

- [ADR-015: FFmpeg 파이프라인 표준화](../adr/ADR-015-ffmpeg-pipeline-standardization_kor.md)
- [Media 모듈 문서](../media/README_kor.md)
- [문제 해결 가이드](../TROUBLESHOOTING_GUIDE.md#videoaudio-sync-problems-a-v-sync)
