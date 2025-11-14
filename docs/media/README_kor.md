# Media 모듈 문서

## 개요

`langflix/media/` 모듈은 LangFlix를 위한 중앙집중식 FFmpeg 유틸리티를 포함합니다. 이 모듈은 오디오 보존과 최적 성능을 보장하는 안정적이고 유지보수 가능한 비디오 및 오디오 처리 함수를 제공합니다.

**최종 업데이트:** 2025-11-14  
**관련 티켓:** TICKET-001, TICKET-033, TICKET-034, TICKET-036

## 목적

이 모듈은 다음을 담당합니다:
- 모든 FFmpeg 관련 로직 중앙집중화
- 오디오 손실 방지를 위한 명시적 스트림 매핑 헬퍼 제공
- 가능한 경우 원본 비디오 포맷 보존 보장 (코덱, 해상도, 픽셀 포맷)
- 안정적인 연결 및 스택 작업 제공
- 최대 안정성을 위한 demuxer 우선 접근법 지원

## 목표

1. 가능한 경우 **원본 비디오 포맷 유지** (코덱, 해상도, 픽셀 포맷)
2. concat/drop 문제를 방지하기 위해 **오디오를 stereo 48k로 강제**
3. 오디오 손실 방지를 위한 **명시적 스트림 매핑** 헬퍼 제공
4. **안전한 프로빙** 및 파라미터 추출 제공
5. 연결 및 반복을 위한 **demuxer 우선** 접근법 지원

## 주요 함수

### 프로빙 함수

#### `run_ffprobe(path: str, timeout: Optional[int] = 30, use_cache: bool = True) -> Dict[str, Any]`
ffprobe를 실행하고 파싱된 JSON을 반환하며, 실패 시 예외 발생.

**TICKET-033 개선사항:** 타임아웃 지원 및 향상된 에러 처리 추가.  
**TICKET-034 개선사항:** 성능 최적화를 위한 지능형 캐싱 레이어 추가.

- **캐싱:** 파일 경로, mtime, 크기를 키로 사용하여 결과 캐싱 (512개 엔트리 LRU 캐시)
- **자동 무효화:** 파일이 수정되면 캐시 자동 무효화 (mtime/크기 변경 감지)
- **성능:** 동일 파일에 대한 중복 ffprobe 호출 제거 (일반 파이프라인에서 60-80% 감소)
- **모니터링:** 캐시 히트/미스 및 통계를 위한 디버그 레벨 로깅
- 안정적인 오류 처리를 위해 subprocess 사용
- 네트워크 마운트에서 무한 대기 방지를 위한 타임아웃 포함 (기본값: 30초)
- 필요 시 ffmpeg-python probe로 fallback
- stderr 출력을 포함한 상세한 에러 메시지 제공

**매개변수:**
- `path`: 비디오 파일 경로
- `timeout`: 타임아웃(초) (기본값: 30, `expression.media.ffprobe.timeout_seconds`로 설정 가능)
- `use_cache`: 캐시 사용 여부 (기본값: True). 실시간 업로드나 처리 중 파일이 변경될 수 있는 경우 False로 설정.

**반환값:**
- ffprobe JSON 출력 딕셔너리 (format 및 streams 정보)

**예외:**
- `TimeoutError`: ffprobe가 타임아웃된 경우
- `FileNotFoundError`: ffprobe를 찾을 수 없는 경우
- `subprocess.CalledProcessError`: ffprobe 명령이 실패한 경우
- `json.JSONDecodeError`: 출력을 JSON으로 파싱할 수 없는 경우
- `OSError`: 캐시 키 생성을 위해 파일에 접근할 수 없는 경우

**캐시 동작:**
```python
# 첫 번째 호출 - 캐시 미스, ffprobe 실행
metadata1 = run_ffprobe("video.mkv")  # 🔍 Cache MISS

# 두 번째 호출 - 캐시 히트, 캐시된 결과 반환
metadata2 = run_ffprobe("video.mkv")  # ✨ Cache HIT

# 파일 수정 후 - 다시 캐시 미스 (자동 무효화)
# ... video.mkv 수정 ...
metadata3 = run_ffprobe("video.mkv")  # 🔍 Cache MISS (파일 변경됨)

# 특수한 경우 캐시 우회
metadata4 = run_ffprobe("realtime_upload.mkv", use_cache=False)  # ⏭️ 캐시 우회됨
```

#### `get_video_params(path: str) -> VideoParams`
파일에서 비디오 파라미터를 추출합니다.

**VideoParams 반환:**
- `codec`: 비디오 코덱 (예: "h264", "hevc")
- `width`: 픽셀 단위 비디오 너비
- `height`: 픽셀 단위 비디오 높이
- `pix_fmt`: 픽셀 포맷 (예: "yuv420p")
- `r_frame_rate`: 프레임 속도 (예: "25/1")

#### `get_audio_params(path: str) -> AudioParams`
파일에서 오디오 파라미터를 추출합니다.

**AudioParams 반환:**
- `codec`: 오디오 코덱 (예: "aac", "mp3")
- `channels`: 오디오 채널 수
- `sample_rate`: Hz 단위 샘플 속도

#### `get_duration_seconds(path: str) -> float`
미디어 지속 시간을 초 단위로 가져옵니다.

- 정확한 지속 시간을 위해 ffprobe 사용 (캐싱 혜택)
- 오류 시 0.0 반환

### 캐시 관리 함수 (TICKET-034)

#### `clear_ffprobe_cache() -> None`
모든 캐시된 ffprobe 결과를 삭제합니다.

**사용 사례:**
- 파일이 자주 교체될 수 있는 테스트 환경
- 필요시 수동 캐시 무효화
- 캐시 관련 문제 디버깅

**예제:**
```python
from langflix.media.ffmpeg_utils import clear_ffprobe_cache

# 모든 캐시된 결과 삭제
clear_ffprobe_cache()
```

#### `get_ffprobe_cache_info() -> Dict[str, int]`
모니터링 및 디버깅을 위한 캐시 통계를 반환합니다.

**반환 딕셔너리:**
- `hits`: 캐시 히트 수
- `misses`: 캐시 미스 수  
- `size`: 현재 캐시된 엔트리 수
- `maxsize`: 최대 캐시 크기 (기본값 512)

**예제:**
```python
from langflix.media.ffmpeg_utils import get_ffprobe_cache_info

# 캐시 통계 가져오기
info = get_ffprobe_cache_info()
print(f"캐시 히트율: {info['hits']}/{info['hits'] + info['misses']}")
print(f"캐시 크기: {info['size']}/{info['maxsize']}")
```

**성능 영향:**
- **캐싱 이전 (TICKET-033):** 에피소드당 70+ ffprobe 호출 (30개 표현 기준)
- **캐싱 이후 (TICKET-034):** ~20-25 ffprobe 호출 (60-80% 감소)
- **평균 절약 시간:** 네트워크 마운트에서 에피소드당 2-5초
- **메모리 사용량:** 캐시 엔트리당 ~50-100KB (최대 512개 ≈ 50MB)

### 연결 함수

#### `repeat_av_demuxer(input_path: str, repeat_count: int, out_path: Path | str) -> None`
**TICKET-001 개선사항:** 최대 안정성을 위해 concat demuxer를 사용하여 AV 세그먼트를 N번 반복.

이것은 표현 반복을 위한 **권장 방법**입니다.

**작동 방식:**
1. 입력의 N개 복사본이 있는 임시 concat 목록 파일 생성
2. 타임스탬프 보존을 위해 concat demuxer (복사 모드) 사용
3. 파이프 입력 실패 시 파일 기반 방법으로 fallback

**이점:**
- 오디오를 안정적으로 보존 (오디오 드랍 없음)
- 타임스탬프 보존 (A-V 동기화 문제 없음)
- 더 간단한 파이프라인 (복잡한 필터 그래프 없음)
- 더 나은 성능 (복사 모드, 재인코딩 없음)

**예제:**
```python
from langflix.media.ffmpeg_utils import repeat_av_demuxer

# 표현 클립을 3번 반복
repeat_av_demuxer("expression_clip.mkv", repeat_count=3, out_path="repeated.mkv")
```

#### `concat_demuxer_if_uniform(list_file: Path | str, out_path: Path | str) -> None`
**TICKET-001 개선사항:** 모든 입력이 균일한 경우 concat demuxer 사용.

**작동 방식:**
1. concat 목록 파일 읽기 (형식: `file 'path'\nfile 'path'\n...`)
2. 첫 번째 파일 프로빙하여 인코딩 파라미터 가져오기
3. 복사 모드로 concat demuxer 사용 (재인코딩 없음)
4. 타임스탬프를 완벽하게 보존

**사용 시기:**
- 모든 입력이 동일한 코덱/해상도/프레임 속도를 가진 경우
- 복사 모드를 원하는 경우 (재인코딩 없음, 더 나은 성능)
- 타임스탬프를 보존해야 하는 경우 (A-V 동기화 문제 방지)

**예제:**
```python
# concat 목록 파일 생성
with open("concat.txt", "w") as f:
    f.write("file 'video1.mkv'\n")
    f.write("file 'video2.mkv'\n")

# demuxer를 사용하여 연결
concat_demuxer_if_uniform("concat.txt", "output.mkv")
```

#### `concat_filter_with_explicit_map(left_path: str, right_path: str, out_path: Path | str) -> None`
v=1,a=1 및 명시적 매핑을 보장하는 filter concat으로 두 세그먼트 연결.

**TICKET-001 개선사항:** 이제 demuxer concat으로 자동 fallback 포함.

**작동 방식:**
1. A-V 동기화 문제를 방지하기 위해 프레임 속도를 25fps로 정규화
2. 타임스탬프 재설정 (setpts/asetpts)을 0에서 시작
3. 명시적 스트림 매핑 사용 (v=1,a=1)
4. filter concat 실패 시 demuxer concat으로 fallback

**사용 시기:**
- 입력 파라미터가 다른 경우 (다른 코덱/해상도)
- 프레임 속도 정규화가 필요한 경우
- Demuxer concat이 실패하는 경우

**예제:**
```python
# 다른 파라미터를 가진 두 비디오 연결
concat_filter_with_explicit_map("video1.mkv", "video2.mkv", "output.mkv")
```

### 스택 함수

#### `hstack_keep_height(left_path: str, right_path: str, out_path: Path | str) -> None`
**TICKET-001 개선사항:** 소스 높이를 유지하면서 두 비디오를 수평으로 스택.

**long-form 레이아웃** (side-by-side)에 사용됩니다.

**작동 방식:**
1. 오른쪽 비디오를 왼쪽 높이와 일치하도록 스케일 (종횡비 유지)
2. 수평으로 스택 (hstack)
3. 왼쪽 입력에서 오디오 사용
4. 원본 비디오 인코딩 파라미터 보존

**예제:**
```python
# Long-form: 왼쪽에 context+expression, 오른쪽에 slide
hstack_keep_height("left_video.mkv", "right_slide.mkv", "long_form.mkv")
```

#### `vstack_keep_width(top_path: str, bottom_path: str, out_path: Path | str) -> None`
**TICKET-001 개선사항:** 소스 너비를 유지하면서 두 비디오를 수직으로 스택.

**short-form 레이아웃** (top-bottom)에 사용됩니다.

**작동 방식:**
1. 아래쪽 비디오를 위쪽 너비와 일치하도록 스케일 (종횡비 유지)
2. 수직으로 스택 (vstack)
3. 위쪽 입력에서 오디오 사용
4. 원본 비디오 인코딩 파라미터 보존

**예제:**
```python
# Short-form: 위쪽에 비디오, 아래쪽에 slide
vstack_keep_width("top_video.mkv", "bottom_slide.mkv", "short_form.mkv")
```

### 오디오 처리 함수

#### `apply_final_audio_gain(input_path: str, out_path: Path | str, gain_factor: float = 1.25) -> None`
**TICKET-001 개선사항:** 별도 최종 패스로 오디오 gain 적용 (간단한 맵, filter_complex 없음).

**작동 방식:**
1. 비디오 및 오디오 스트림 추출
2. 오디오에만 볼륨 필터 적용 (gain_factor, 기본값 1.25 = +25%)
3. 비디오 스트림 복사 (가능한 경우 재인코딩 없음)
4. 오디오 인코딩 (필터로 인해 인코딩 필요)

**사용 시기:**
- 파이프라인의 최종 단계 (레이아웃 완료 후)
- 오디오 볼륨 부스트 필요
- 비디오 스트림 보존 원함

**예제:**
```python
# 최종 오디오 부스트 적용 (+25%)
apply_final_audio_gain("final_video.mkv", "output.mkv", gain_factor=1.25)
```

### 인코딩 헬퍼

#### `make_video_encode_args_from_source(source_path: str) -> Dict[str, Any]`
가능한 한 소스 비디오와 일치하도록 인코더 인수를 생성합니다.

- 가능한 경우 소스 코덱 재사용 (h264, hevc, vp9, prores)
- 해상도 보존
- 필요한 경우가 아니면 픽셀 포맷 강제하지 않음

#### `make_audio_encode_args(normalize: bool = False) -> Dict[str, Any]`
오디오 인코딩 인수를 가져옵니다.

- `normalize=True`인 경우: stereo/48k로 정규화 (aac 코덱)
- `normalize=False`인 경우: 복사 모드 사용 (재인코딩 없음)

#### `make_audio_encode_args_copy() -> Dict[str, Any]`
재인코딩 없이 오디오 복사 선호.

- `{"acodec": "copy"}` 반환

### 유틸리티 함수

#### `should_copy_video(input_path: str) -> bool`
`-c:v copy`를 안전하게 사용할 수 있는지 결정합니다.

- 비디오에 유효한 코덱/너비/높이가 있으면 True 반환
- 복사 모드 가능 여부 결정에 사용

#### `log_media_params(path: str, label: str = "media") -> None`
디버깅을 위해 미디어 파라미터를 로깅합니다.

- 비디오 코덱, 해상도, 픽셀 포맷 로깅
- 오디오 코덱, 채널, 샘플 속도 로깅

## 아키텍처 패턴

### Demuxer 우선 접근법 (TICKET-001)

**우선순위 순서:**
1. **Demuxer concat** (선호) - 복사 모드, 타임스탬프 보존
2. **Filter concat** (fallback) - 파라미터가 다르거나 demuxer가 실패하는 경우

**이점:**
- 최대 안정성 (더 적은 오디오 드랍)
- 더 나은 성능 (복사 모드, 재인코딩 없음)
- 타임스탬프 보존 (A-V 동기화 문제 없음)
- 더 간단한 파이프라인 그래프

### 명시적 스트림 매핑

**오디오 보존에 중요:**
- filter concat에서 항상 `v=1,a=1` 사용
- 출력에서 항상 비디오 및 오디오 스트림을 명시적으로 매핑
- `output_with_explicit_streams()` 헬퍼 사용

### 복사 모드 선호

**복사 모드 사용 시기:**
- 필터가 적용되지 않은 경우
- 파라미터가 균일한 경우
- 타임스탬프 보존이 중요한 경우

**인코딩 사용 시기:**
- 필터가 필요한 경우
- 파라미터 정규화가 필요한 경우
- 포맷 변환이 필요한 경우

## 일반 작업

### 새 스택 작업 추가

1. `ffmpeg_utils.py`에 새 함수 생성 (예: `grid_keep_aspect()`)
2. 동일한 패턴 사용: 파라미터 프로빙 → 스케일 → 스택 → 명시적 출력
3. 주요 입력에서 오디오 보존
4. `tests/integration/test_media_pipeline_*.py`에 테스트 추가

### 연결 로직 수정

1. 가능한 경우 demuxer concat 선호 (복사 모드)
2. fallback으로 filter concat 사용 (프레임 속도 정규화 포함)
3. 항상 명시적 스트림 매핑 포함
4. 방법 간 자동 fallback 추가

### 오디오 드랍 디버깅

1. **명시적 매핑 확인:**
   ```python
   # filter concat에서 v=1,a=1 보장
   concat_node = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1, n=2)
   ```

2. **오디오 존재 확인:**
   ```bash
   ffprobe -v error -show_entries stream=codec_type input.mkv | grep audio
   ```

3. **복사 모드 확인:**
   ```python
   # 인코딩 인수에서 "acodec=copy" 찾기
   encode_args = make_audio_encode_args_copy()
   ```

## 주의사항 및 참고사항

### Demuxer Concat 요구사항

⚠️ **중요:** Demuxer concat에는 다음이 필요합니다:
- 입력 간 균일한 코덱
- 균일한 해상도 (또는 호환 가능한 종횡비)
- 균일한 프레임 속도 (또는 호환 가능한 속도)
- 동일한 컨테이너 포맷

**파라미터가 다른 경우:** 대신 `concat_filter_with_explicit_map()` 사용.

### 프레임 속도 정규화

⚠️ **A-V 동기화에 중요:** Filter concat은 프레임 속도를 25fps로 정규화합니다:
- 재생 중 정지 방지
- 부드러운 A-V 동기화 보장
- 타임스탬프를 0에서 시작하도록 재설정

**A-V 동기화 문제가 보이는 경우:** 프레임 속도 정규화가 적용되었는지 확인.

### 복사 모드 제한사항

⚠️ **다음과 같은 경우 복사 모드를 사용할 수 없음:**
- 필터가 적용되는 경우 (fps, scale, volume 등)
- 파라미터 정규화가 필요한 경우
- 포맷 변환이 필요한 경우

**필터 또는 정규화가 필요한 경우:** 인코딩 사용.

### 오디오 처리 순서

✅ **모범 사례:** 끝에서 오디오 변환 적용:
1. 비디오 파이프라인 빌드 (concat, stack 등)
2. 최종 단계로 오디오 gain 적용
3. 중간 파이프라인 오디오 변환 없음

**이유:** 파이프라인 전체에서 오디오 보존, 최종 단계에서만 수정.

## ExpressionMediaSlicer 모듈

### 개요
`ExpressionMediaSlicer` 클래스(`langflix/media/expression_slicer.py`)는 정밀한 타임스탬프를 사용하여 FFmpeg로 표현식에 대한 미디어 파일을 슬라이싱합니다.

**TICKET-036 개선사항:**
- NameError 버그 수정 (올바른 변수명 사용)
- 리소스 고갈 방지를 위한 Semaphore 기반 동시성 제어 추가
- 실패/부분 슬라이스 자동 정리 구현
- 설정 가능한 동시성 제한 추가

### 주요 기능

#### 동시성 제어
**문제:** 배치 슬라이싱 작업이 무제한 FFmpeg 프로세스를 생성하여 리소스 제한 서버에서 CPU 포화 및 OOM을 유발할 수 있습니다.

**해결책:** Asyncio Semaphore 기반 동시성 제한:
- 기본값: CPU 코어 수 / 2 (`expression.media.slicing.max_concurrent`로 설정 가능)
- 인스턴스당 세마포어로 공정한 리소스 사용 보장
- 성공 또는 실패 시 자동 릴리스

**설정:**
```yaml
expression:
  media:
    slicing:
      max_concurrent: null  # 자동 감지 (CPU/2) 또는 숫자 지정
      buffer_start: 0.2     # 표현식 시작 전 버퍼 (초)
      buffer_end: 0.2       # 표현식 종료 후 버퍼 (초)
```

### 주요 메서드

#### `__init__(storage_backend, output_dir, quality='high', max_concurrency=None)`
선택적 동시성 오버라이드로 slicer를 초기화합니다.

**매개변수:**
- `storage_backend`: 슬라이싱된 비디오 저장을 위한 StorageBackend
- `output_dir`: 로컬 출력 디렉토리
- `quality`: 비디오 품질 프리셋 ('low', 'medium', 'high', 'lossless')
- `max_concurrency`: 기본 동시성 제한 오버라이드 (None = 설정 사용)

#### `slice_expression(media_path, expression_data, media_id) -> str`
미디어 파일에서 단일 표현식을 슬라이싱합니다.

**매개변수:**
- `media_path`: 소스 미디어 파일 경로
- `expression_data`: `{'expression', 'start_time', 'end_time'}` 딕셔너리
- `media_id`: 고유 미디어 식별자

**반환값:**
- 슬라이싱된 비디오 경로 (클라우드 스토리지 경로 또는 로컬)

**에러 처리 (TICKET-036):**
- 실패/부분 파일 자동 정리
- 표현식 컨텍스트가 포함된 상세한 에러 메시지
- 업로드 실패 시 로컬 스토리지로 우아한 fallback

#### `slice_multiple_expressions(media_path, expressions, media_id) -> List[str]`
동시성 제어로 여러 표현식을 슬라이싱합니다.

**매개변수:**
- `media_path`: 소스 미디어 파일 경로
- `expressions`: 표현식 딕셔너리 리스트
- `media_id`: 고유 미디어 식별자

**반환값:**
- 성공적으로 슬라이싱된 비디오 경로 리스트 (실패한 슬라이스 제외)

**동작 (TICKET-036):**
- 각 슬라이스 작업을 세마포어 가드로 감쌉니다
- 동시 FFmpeg 프로세스를 설정된 최대값으로 제한
- 성공한 결과만 반환
- 상세한 통계 로깅 (성공/실패 개수)

**예제:**
```python
from langflix.media.expression_slicer import ExpressionMediaSlicer
from langflix.storage import get_storage_backend

slicer = ExpressionMediaSlicer(
    storage_backend=get_storage_backend(),
    output_dir=Path("./output"),
    quality='high',
    max_concurrency=4  # 4개 동시 작업으로 제한
)

expressions = [
    {'expression': 'Hello world', 'start_time': 1.0, 'end_time': 3.0},
    {'expression': 'Nice to meet you', 'start_time': 5.0, 'end_time': 7.0},
    # ... 더 많은 표현식
]

# 동시성 제어로 슬라이싱 (최대 4개씩)
paths = await slicer.slice_multiple_expressions(
    media_path='/path/to/video.mp4',
    expressions=expressions,
    media_id='video123'
)

print(f"{len(paths)}개의 표현식을 성공적으로 슬라이싱했습니다")
```

### 성능 영향 (TICKET-036)

**이전:**
- 무제한 동시 FFmpeg 프로세스
- 20+ 표현식에서 CPU 100% 포화
- OOM을 유발하는 메모리 급증
- 서버 불안정

**이후:**
- 제어된 동시성 (기본값: CPU/2)
- CPU 사용량이 제한 내 유지
- 안정적인 메모리 사용
- 예측 가능한 리소스 소비

**메트릭 (8코어 서버, 20개 표현식):**
- 이전: 20개 동시 FFmpeg 프로세스, CPU 100%
- 이후 (동시성=4): 최대 4개 동시, CPU ~60-70%
- 리소스 사용량 ~40% 감소

### 버그 수정 (TICKET-036)

#### NameError: 'aligned_expressions' not defined
**문제:** 루프 변수가 함수 매개변수 `expressions` 대신 `aligned_expressions`를 잘못 참조했습니다.

**수정:** 모든 참조를 올바른 `expressions` 매개변수를 사용하도록 변경했습니다.

#### NameError: 'aligned_expression' not defined  
**문제:** 에러 처리가 정의되지 않은 `aligned_expression.expression`을 참조했습니다.

**수정:** `expression_data.get('expression', 'unknown')`을 사용하도록 변경했습니다.

### 테스트

`tests/unit/test_expression_slicer.py`의 단위 테스트:
- ✅ 세마포어 초기화 및 제한
- ✅ 동시 실행 강제 (최대값 초과하지 않음)
- ✅ 성공 시 세마포어 릴리스
- ✅ 실패 시 세마포어 릴리스
- ✅ NameError 버그 수정 검증
- ✅ 실패한 슬라이스 정리 로직
- ✅ 설정 통합
- ✅ 혼합 성공/실패 처리

모든 11개 테스트 통과 ✅

## MediaScanner 모듈

### 개요
`MediaScanner` 클래스(`langflix/media/media_scanner.py`)는 미디어 디렉토리를 스캔하여 비디오 파일과 관련 자막 파일을 찾습니다.

**TICKET-033 개선사항:** 향상된 에러 처리 및 파일 접근 가능성 확인.

### 주요 메서드

#### `_get_video_metadata(video_path: Path) -> Dict[str, Any]`
포괄적인 에러 처리를 통해 ffprobe를 사용하여 비디오 메타데이터를 추출합니다.

**개선사항 (TICKET-033):**
- 프로빙 전 파일 접근 가능성 사전 확인
- 구성 가능한 타임아웃을 지원하는 개선된 `run_ffprobe()` 함수 사용
- stderr 출력을 포함한 상세한 에러 로깅 제공
- 특정 예외 타입 처리: `CalledProcessError`, `FileNotFoundError`, `JSONDecodeError`, `PermissionError`, `TimeoutError`
- 실패 시 빈 dict 반환 (우아한 성능 저하)

**에러 처리:**
- 파일 없음: 경고 로그 및 빈 dict 반환
- 권한 거부: TrueNAS 마운트 가이드와 함께 에러 로그
- 타임아웃: 네트워크 마운트 문제를 나타내는 에러 로그
- FFprobe 에러: 디버깅을 위한 stderr 출력 로그
- JSON 파싱 에러: 손상된 파일 또는 FFprobe 문제를 나타내는 에러 로그

#### 설정
- 기본 타임아웃은 `expression.media.ffprobe.timeout_seconds`로 구성하며 기본값은 **30초**(최소 **1초**)입니다.
- `run_ffprobe` 호출 시 명시적으로 타임아웃을 전달하지 않으면 위 설정이 자동 적용됩니다.

#### `_check_file_accessible(video_path: Path) -> Tuple[bool, Optional[str]]`
처리 전 비디오 파일 접근 가능 여부를 확인합니다.

**확인 사항:**
- 파일 존재
- 경로가 파일인지 (디렉토리가 아닌지)
- 파일 읽기 가능 여부
- 파일이 비어있지 않은지

**반환:**
- 접근 가능한 경우: `(True, None)`
- 접근 불가능한 경우: `(False, error_message)`

## 테스트

### 단위 테스트
- `tests/unit/test_media_scanner.py` - MediaScanner 에러 처리 및 메타데이터 추출
  - 파일 접근 가능성 확인
  - FFprobe 에러 시나리오
  - 타임아웃 처리
  - 권한 에러
  - JSON 파싱 에러

### 통합 테스트
- `tests/integration/test_media_pipeline_audio.py` - 파이프라인을 통한 오디오 보존
- `tests/functional/test_educational_video.py` - 종단 간 비디오 생성

### 검증 스크립트
- `tools/verify_media_pipeline.py` - 포괄적인 파이프라인 검증
  - Demuxer 반복 테스트
  - 연결 작업 테스트
  - 스택 작업 테스트
  - ffprobe로 오디오 존재 확인

## 관련 문서

- [ADR-015: FFmpeg 파이프라인 표준화](../adr/ADR-015-ffmpeg-pipeline-standardization_kor.md)
- [Core 모듈 문서](../core/README_kor.md)
- [문제 해결 가이드](../TROUBLESHOOTING_GUIDE.md#videoaudio-sync-problems-a-v-sync)


