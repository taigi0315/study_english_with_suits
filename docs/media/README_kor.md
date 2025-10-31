# Media 모듈 문서

## 개요

`langflix/media/` 모듈은 LangFlix를 위한 중앙집중식 FFmpeg 유틸리티를 포함합니다. 이 모듈은 오디오 보존과 최적 성능을 보장하는 안정적이고 유지보수 가능한 비디오 및 오디오 처리 함수를 제공합니다.

**최종 업데이트:** 2025-01-30  
**관련 티켓:** TICKET-001

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

#### `run_ffprobe(path: str) -> Dict[str, Any]`
ffprobe를 실행하고 파싱된 JSON을 반환하며, 실패 시 예외 발생.

- 안정적인 오류 처리를 위해 subprocess 사용
- 필요 시 ffmpeg-python probe로 fallback

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

- 정확한 지속 시간을 위해 ffprobe 사용
- 오류 시 0.0 반환

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

## 테스트

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

