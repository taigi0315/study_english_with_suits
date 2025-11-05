# Core 모듈 문서

## 개요

`langflix/core/` 모듈은 LangFlix의 핵심 비디오 편집 기능을 포함합니다. 이 모듈은 long-form (side-by-side) 및 short-form (vertical) 비디오 레이아웃을 포함한 교육용 비디오 시퀀스 생성을 조율합니다.

**최종 업데이트:** 2025-11-05  
**관련 티켓:** TICKET-001, TICKET-005, TICKET-024, TICKET-025

## 목적

이 모듈은 다음을 담당합니다:
- 컨텍스트 클립과 표현 반복이 포함된 교육용 비디오 시퀀스 생성
- side-by-side 레이아웃(hstack)을 가진 long-form 비디오 생성
- vertical 레이아웃(vstack)을 가진 short-form 비디오 생성
- 자막 오버레이 및 교육 슬라이드 관리
- 파이프라인 전체에서 오디오/비디오 동기화 조율

## 주요 구성 요소

### LangFlixPipeline 클래스

TV 쇼 콘텐츠를 학습 자료로 처리하는 주요 파이프라인 클래스입니다.

**위치:** `langflix/main.py`

**진행 상황 콜백 지원 (TICKET-001):**
- `__init__()`에 선택적 `progress_callback` 파라미터 추가
- 콜백 시그니처: `(progress: int, message: str) -> None`
- 주요 파이프라인 단계에서 자동으로 진행 상황 리포트:
  - 10%: 자막 파싱
  - 20%: 자막 청킹
  - 30%: 표현 분석
  - 50%: 표현 처리
  - 70%: 교육용 비디오 생성
  - 80%: short-format 비디오 생성
  - 95%: 요약 생성
  - 98%: 임시 파일 정리
  - 100%: 파이프라인 성공적으로 완료

**사용 예시:**
```python
def progress_callback(progress: int, message: str):
    print(f"진행 상황: {progress}% - {message}")

pipeline = LangFlixPipeline(
    subtitle_file="path/to/subtitle.srt",
    video_dir="assets/media",
    output_dir="output",
    language_code="ko",
    progress_callback=progress_callback  # 선택사항
)
```

**병렬 LLM 처리 (TICKET-001):**
- 표현 분석이 여러 청크에 대해 병렬 처리를 지원합니다
- 자동으로 `ExpressionBatchProcessor`를 사용하여 청크를 동시에 처리합니다
- `default.yaml`의 `expression.llm.parallel_processing`을 통해 설정 가능합니다

**작동 방식:**
1. `_analyze_expressions()`는 병렬 처리가 활성화되어 있고 여러 청크가 있는지 확인합니다
2. 활성화되어 있고 여러 청크가 사용 가능한 경우(그리고 test_mode가 아닌 경우), `_analyze_expressions_parallel()`을 사용합니다
3. 그렇지 않으면 `_analyze_expressions_sequential()`을 통한 순차 처리로 폴백합니다
4. 병렬 처리는 `ThreadPoolExecutor`를 사용하여 병렬 작업을 생성하는 `ExpressionBatchProcessor`를 사용합니다
5. 진행 상황은 청크가 완료됨에 따라 보고됩니다 (순차적으로가 아님)

**설정:**
```yaml
expression:
  llm:
    parallel_processing:
      enabled: true  # 병렬 처리 활성화
      max_workers: null  # null = 자동 감지 (min(cpu_count(), 5))
      timeout_per_chunk: 300  # 초
```

**병렬 처리가 사용되는 경우:**
- ✅ 병렬 처리 활성화 (`expression.llm.parallel_processing.enabled: true`)
- ✅ 처리할 여러 청크 (`len(chunks) > 1`)
- ✅ 테스트 모드 아님 (`test_mode=False`)

**순차 처리가 사용되는 경우:**
- ❌ 병렬 처리 비활성화
- ❌ 단일 청크 (병렬화의 이점 없음)
- ❌ 테스트 모드 (`test_mode=True`) - 디버깅을 위해 항상 순차 처리

**성능 이점:**
- 10개 이상의 청크에 대해 3-5배 빠른 처리
- 각 LLM API 호출을 기다리는 대신 청크를 동시에 처리
- 보수적인 기본값: Gemini API rate limit을 피하기 위해 최대 5개 worker

**예시:**
```python
# 병렬 처리 활성화 상태 (기본값)
pipeline = LangFlixPipeline(...)
result = pipeline.run(
    max_expressions=10,
    test_mode=False  # 여러 청크가 있는 경우 병렬 처리 사용
)

# 로그에 표시됨:
# "Using PARALLEL processing for 15 chunks"
# "Starting parallel analysis of 15 chunks with 5 workers"
# "Parallel analysis complete in 45.2s"
```

**컨텍스트당 다중 표현식 지원 (TICKET-008):**
- 동일한 `context_start_time`과 `context_end_time`을 공유하는 표현식이 자동으로 그룹화됩니다
- 그룹은 단일 컨텍스트 비디오 클립을 공유합니다 (효율성 향상)
- 각 표현식은 여전히 자체 교육용 비디오를 받습니다 (분리 모드, 하위 호환성)
- `expression.llm.allow_multiple_expressions` 및 `expression.llm.max_expressions_per_context`를 통해 설정 가능

**작동 방식:**
1. 표현 분석 후, `group_expressions_by_context()`가 공유 컨텍스트 시간으로 표현식을 그룹화합니다
2. `_process_expressions()`는 그룹당 하나의 컨텍스트 클립을 추출합니다 (그룹의 모든 표현식이 공유)
3. 각 표현식에 대해 별도의 자막 파일이 생성됩니다
4. `_create_educational_videos()`는 다음 순서로 비디오를 생성합니다:
   - **다중 표현식 그룹**: 먼저 다중 표현식 슬라이드가 있는 컨텍스트 비디오 생성 (왼쪽: 컨텍스트 비디오, 오른쪽: 모든 표현식을 보여주는 슬라이드)
   - **각 표현식**: 개별 교육용 비디오 생성 (왼쪽: 다중 표현식 그룹의 경우 표현 반복만, 단일 표현식 그룹의 경우 컨텍스트 + 표현 반복; 오른쪽: 표현식의 자체 슬라이드)
5. 컨텍스트 클립은 중복 추출을 방지하기 위해 캐시됩니다

**비디오 출력 구조:**
- **다중 표현식 그룹** (2개 이상의 표현식):
  1. 컨텍스트 비디오: 왼쪽 (컨텍스트 비디오) | 오른쪽 (모든 표현식을 포함한 다중 표현식 슬라이드)
  2. 표현식 1 비디오: 왼쪽 (표현 반복만) | 오른쪽 (표현식 1의 슬라이드)
  3. 표현식 2 비디오: 왼쪽 (표현 반복만) | 오른쪽 (표현식 2의 슬라이드)
  
- **단일 표현식 그룹** (하위 호환성):
  1. 표현식 비디오: 왼쪽 (컨텍스트 + 표현 반복) | 오른쪽 (표현식의 슬라이드)

**설정:**
```yaml
expression:
  llm:
    allow_multiple_expressions: true  # 기능 활성화/비활성화
    max_expressions_per_context: 3    # 컨텍스트당 최대 표현식 수
  educational_video_mode: "separate"  # "separate" 또는 "combined" (Phase 2)
```

**ExpressionGroup 모델:**
- `ExpressionGroup`은 동일한 컨텍스트를 공유하는 여러 `ExpressionAnalysis` 객체를 포함합니다
- 그룹의 모든 표현식이 일치하는 `context_start_time`과 `context_end_time`을 가지고 있는지 검증합니다
- 쉽게 접근할 수 있도록 반복, 인덱싱, 길이 쿼리를 지원합니다

**이점:**
- 동일한 콘텐츠에서 더 많은 교육적 가치 (하나의 컨텍스트에서 여러 표현식)
- 처리 효율성: 공유 컨텍스트 클립이 중복 비디오 추출을 줄입니다
- 리소스 최적화: 낮은 스토리지 사용량 및 더 빠른 처리
- 하위 호환성: 단일 표현식이 자동으로 그룹 1개가 됩니다

**예시:**
```python
# 그룹화는 활성화된 경우 자동으로 수행됩니다 (기본값)
pipeline = LangFlixPipeline(
    subtitle_file="path/to/subtitle.srt",
    video_dir="assets/media",
    output_dir="output",
    enable_expression_grouping=True  # 기본값: True
)

# run() 후, 그룹에 접근:
groups = pipeline.expression_groups
for group in groups:
    print(f"그룹에 {len(group)}개의 표현식이 있습니다")
    for expr in group:
        print(f"  - {expr.expression}")
```

**그룹화가 사용되는 경우:**
- ✅ `enable_expression_grouping=True` (기본값)
- ✅ 여러 표현식이 동일한 컨텍스트 시간을 공유
- ✅ 설정에서 기능 활성화 (`expression.llm.allow_multiple_expressions: true`)

**단일 표현식 그룹이 생성되는 경우:**
- ❌ 그룹화 비활성화 (`enable_expression_grouping=False`)
- ❌ 모든 표현식이 다른 컨텍스트를 가짐 (그룹화 불필요)
- ❌ 설정에서 기능 비활성화

**효율성 향상:**
- 3개의 표현식이 동일한 컨텍스트를 공유하는 경우, 3개 대신 1개의 컨텍스트 클립만 추출됩니다
- 예시: 3개 그룹의 10개 표현식 → 10개 대신 3개의 컨텍스트 클립 (70% 감소)

### VideoEditor 클래스

비디오 생성을 조율하는 주요 클래스입니다.

**위치:** `langflix/core/video_editor.py`

**에러 핸들러 통합 (TICKET-005):**
- `create_educational_sequence()`는 구조화된 에러 리포팅을 위해 `@handle_error_decorator`로 래핑됨
- `create_short_format_video()`는 구조화된 에러 리포팅을 위해 `@handle_error_decorator`로 래핑됨
- `_create_timeline_from_tts()`는 일시적 실패 시 자동 재시도를 위해 `@retry_on_error` 데코레이터 사용 (최대 2회, 1초 지연)
- 모든 에러는 에러 핸들러를 통해 컨텍스트(operation, component)와 함께 자동 로깅됨
- 에러 리포트에는 디버깅을 위한 작업 컨텍스트가 포함됨

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

### 비디오 생성 과정

비디오 생성 과정은 명확한 계층 구조를 따릅니다:

#### 1. Context Video (원본 비디오 슬라이스)
**위치:** `langflix/core/video_processor.py::extract_clip()`

표현식 주변의 컨텍스트를 포함하는 원본 비디오의 슬라이스를 생성합니다.

**과정:**
- 원본 비디오 파일에서 클립 추출
- 표현식의 `context_start_time`과 `context_end_time` 사용
- FFmpeg 명령: `ffmpeg -ss {start_time} -i {original_video} -t {duration} -c:v libx264 -c:a aac`
- 출력: 원시 컨텍스트 비디오 클립 (자막 없음, 원본 해상도)

**예시:**
```python
# 원본 비디오: 00:00:00 - 00:45:00 (전체 에피소드)
# 표현식 컨텍스트: 00:05:30 - 00:06:10
# Context video: 00:05:30 - 00:06:10 (40초 슬라이스)
```

**핵심 사항:**
- 원본 비디오에서 직접 슬라이스
- 수정 없음 (원본 품질 보존)
- 비디오 및 오디오 스트림 모두 포함
- 모든 후속 처리의 기본으로 사용

#### 2. Context Video with Subtitles (자막 오버레이)
**위치:** `langflix/core/video_editor.py::_add_subtitles_to_context()`

FFmpeg의 subtitle 필터를 사용하여 컨텍스트 비디오에 이중 언어 자막을 추가합니다.

**과정:**
1. 이중 언어 자막 파일 (`.srt` 형식) 찾기 또는 생성
   - 자막 파일은 `SubtitleProcessor.create_dual_language_subtitle_file()`에 의해 생성됨
   - 타임스탬프는 이미 `context_start_time` 기준으로 조정됨 (00:00:00부터 시작)
2. FFmpeg `subtitles` 필터를 사용하여 자막 적용
   - FFmpeg 명령: `ffmpeg -i {context_video} -vf "subtitles={subtitle_file}"`
   - 자막이 비디오에 하드코딩됨 (burned in)
3. 출력: 자막이 오버레이된 컨텍스트 비디오

**자막 파일 생성:**
- `SubtitleProcessor.create_dual_language_subtitle_file()`에 의해 생성됨
- 컨텍스트 시간 범위 내의 원본 SRT 파일에서 자막 추출
- 타임스탬프 조정: `relative_time = absolute_time - context_start_time`
- 이중 언어 SRT 생성 (원본 + 번역)

**예시:**
```python
# Context video: 00:05:30 - 00:06:10 (원본에서)
# 자막 파일의 타임스탬프가 조정됨:
#   원본: 00:05:35,000 --> 00:05:37,500 "Hello"
#   조정: 00:00:05,000 --> 00:00:07,500 "Hello"
# 결과: 00:00:00부터 시작하는 자막이 포함된 컨텍스트 비디오
```

**핵심 사항:**
- 자막이 비디오에 하드코딩됨 (별도 트랙 아님)
- 타임스탬프는 컨텍스트 비디오와 일치하도록 조정됨 (0부터 시작)
- 이중 언어 형식: 원본 텍스트 + 번역
- 표현식 추출에 재사용됨 (자막 동기화 보장)

#### 3. Expression Video (컨텍스트 비디오 슬라이스)
**위치:** `langflix/core/video_editor.py::create_multi_expression_sequence()` (line 500-507)

자막이 포함된 컨텍스트 비디오에서 표현식 세그먼트를 추출합니다.

**과정:**
1. 소스로 `context_with_subtitles` 사용 (원본 비디오 아님)
   - **중요:** 자막 동기화를 보장하기 위해 자막이 적용된 컨텍스트를 사용해야 함
2. 컨텍스트 비디오 내의 상대 타임스탬프 계산:
   - `relative_start = expression_start_time - context_start_time`
   - `relative_end = expression_end_time - context_start_time`
3. 상대 타임스탬프를 사용하여 FFmpeg로 클립 추출:
   - FFmpeg 명령: `ffmpeg -ss {relative_start} -i {context_with_subtitles} -t {duration}`
   - 타임스탬프 리셋: `setpts=PTS-STARTPTS` (00:00:00부터 시작)
4. 다중 표현식 그룹의 경우: `pad` 필터를 사용하여 2560x720 해상도 일치
   - 왼쪽 절반에 원본 비디오 배치 (0,0)
   - 오른쪽 절반을 검은색으로 채움 (원본 품질 유지)
5. 출력: 자막이 동기화된 표현식 비디오 클립

**예시:**
```python
# Context video: 00:05:30 - 00:06:10 (40초, 자막 포함)
# Expression: 00:05:50 - 00:05:55 (컨텍스트 내)
# Relative: 00:00:20 - 00:00:25 (컨텍스트 비디오 내)
# Expression clip: context_with_subtitles에서 00:00:20 - 00:00:25
# 결과: 자막이 동기화된 5초 표현식 클립
```

**핵심 사항:**
- **반드시** `context_with_subtitles` 사용 (원본 또는 원시 컨텍스트 아님)
- 자막이 이미 동기화됨 (조정 불필요)
- 연결을 위해 타임스탬프를 0으로 리셋
- 원본 해상도 보존 (레이아웃 호환성을 위한 pad 필터)

**이 순서가 중요한 이유:**
1. Context video는 깨끗한 슬라이스 (처리 없음)
2. 자막을 컨텍스트에 한 번만 추가 (효율적, 동기화됨)
3. 자막이 적용된 컨텍스트에서 표현식 추출 (동기화 보장)
4. 자막 타임스탬프 문제 없음 (모두 컨텍스트 기준 상대)

### 헬퍼 메서드

#### `_add_subtitles_to_context()`
컨텍스트 비디오에 이중 언어 자막을 추가합니다.

**개선사항 (TICKET-001 Phase 4):**
- 파일이 존재하는지 확인하고 재사용 (long-form과 short-form 간 충돌 방지)
- 일관된 자막 스타일링 사용

#### 파일명 Sanitization
`VideoEditor` 클래스는 코드베이스 전반에서 일관된 파일명 sanitization을 위해 `langflix.utils.filename_utils`의 `sanitize_for_expression_filename()`을 사용합니다. 자세한 내용은 [Filename Utils 문서](../utils/filename_utils_kor.md)를 참조하세요.

**TICKET-001 Phase 4에 중요:**
- 모든 파일명 sanitization은 이제 `langflix.utils.filename_utils`의 `sanitize_for_expression_filename()`을 사용합니다
- 코드베이스 전반에서 일관된 sanitization 보장 (TICKET-004)
- 표현 일치를 보장하기 위해 작업 생성과 비디오 파일 명명 간에 정확히 일치해야 합니다

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

### ExpressionAnalyzer 클래스

Gemini API를 사용하여 자막 청크를 분석하는 클래스입니다.

**위치:** `langflix/core/expression_analyzer.py`

**에러 핸들러 통합 (TICKET-005):**
- `analyze_chunk()`는 구조화된 에러 리포팅을 위해 `@handle_error_decorator`로 래핑됨
- `_generate_content_with_retry()`는 이제 각 재시도 시도마다 에러 핸들러에 에러를 리포팅
- 에러 컨텍스트에 포함: `operation`, `component`, `max_retries`, `attempt`, `prompt_length`
- 에러는 자동으로 분류됨 (타임아웃/연결 에러의 경우 NETWORK, 파싱 에러의 경우 PROCESSING)
- 에러 리포트에는 API 실패 디버깅을 위한 재시도 시도 정보가 포함됨

**주요 기능:**
- API 실패 시 지수 백오프를 사용한 자동 재시도
- 모든 API 에러에 대한 구조화된 에러 리포팅
- 더 나은 모니터링을 위한 에러 카테고리화
- 디버깅을 위한 상세한 에러 컨텍스트

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
- `langflix/utils/filename_utils.py::sanitize_for_expression_filename()` - [Filename Utils 문서](../utils/filename_utils_kor.md) 참조
- `langflix/api/routes/jobs.py` (작업 생성 시 정리)

**불일치 시 문제:** Short-form에서 첫 번째 표현 누락 (TICKET-001 이슈 3)

**해결책:** 두 위치에서 `langflix.utils.filename_utils`의 `sanitize_for_expression_filename()` 사용 (TICKET-004):
```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

sanitized = sanitize_for_expression_filename(expression_text)
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
