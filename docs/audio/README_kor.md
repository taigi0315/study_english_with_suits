# Audio 모듈 문서

## 개요

`langflix/audio/` 모듈은 LangFlix를 위한 오디오 처리 기능을 제공하며, 오디오 최적화, 원본 오디오 추출, 교육용 콘텐츠를 위한 타임라인 생성 등을 포함합니다.

**최종 업데이트:** 2025-01-30

## 목적

이 모듈의 주요 역할:
- 오디오 품질 최적화 및 향상
- 원본 비디오 파일에서 오디오 세그먼트 추출
- 교육 목적의 반복 패턴을 가진 오디오 타임라인 생성
- 오디오 포맷 변환 및 동기화 관리

## 주요 구성 요소

### AudioOptimizer

**위치:** `langflix/audio/audio_optimizer.py`

고급 오디오 최적화 시스템으로 다음을 제공:
- 목표 음량 레벨로 오디오 정규화
- 노이즈 감소
- 다이나믹 레인지 압축
- 오디오 품질 분석 및 메트릭

**주요 메서드:**

```python
def optimize_audio(
    input_path: str,
    output_path: str,
    optimization_level: str = "medium"
) -> AudioQualityMetrics:
    """
    교육용 콘텐츠를 위한 오디오 파일 최적화.
    
    최적화 레벨:
    - low: 기본 음량 정규화
    - medium: 정규화 + 필터링 + 압축
    - high: 이퀄라이제이션을 포함한 전체 향상
    """
```

**오디오 품질 메트릭:**
- `loudness_lufs`: LUFS 단위의 통합 음량
- `peak_db`: dB 단위의 피크 레벨
- `dynamic_range`: 다이나믹 레인지
- `noise_floor_db`: 노이즈 플로어 레벨
- `frequency_response`: 주파수 응답 데이터
- `distortion_percent`: 왜곡 비율

**사용 예시:**

```python
from langflix.audio.audio_optimizer import AudioOptimizer, AudioOptimizationConfig

config = AudioOptimizationConfig(
    target_loudness=-23.0,
    noise_reduction=0.3,
    enhance_clarity=True
)

optimizer = AudioOptimizer(config)
metrics = optimizer.optimize_audio(
    "input.wav",
    "output.wav",
    optimization_level="medium"
)

print(f"음량: {metrics.loudness_lufs} LUFS")
print(f"피크: {metrics.peak_db} dB")
```

### OriginalAudioExtractor

**위치:** `langflix/audio/original_audio_extractor.py`

TTS가 비활성화된 경우 원본 비디오 파일에서 오디오 세그먼트를 추출하며, 일관성을 위해 TTS와 동일한 3x 반복 타임라인 패턴을 생성합니다.

**주요 메서드:**

```python
def extract_expression_audio(
    self, 
    expression: ExpressionAnalysis, 
    output_path: Path, 
    audio_format: str = "wav"
) -> Tuple[Path, float]:
    """
    원본 비디오에서 표현식의 오디오 세그먼트 추출.
    
    Args:
        expression: 타임스탬프가 포함된 ExpressionAnalysis
        output_path: 추출된 오디오의 출력 경로
        audio_format: 오디오 포맷 (wav 또는 mp3)
        
    Returns:
        (오디오_파일_경로, 초_단위_길이) 튜플
    """
```

```python
def create_audio_timeline(
    self,
    expression: ExpressionAnalysis,
    output_dir: Path,
    expression_index: int = 0,
    audio_format: str = "wav",
    repeat_count: int = None
) -> Tuple[Path, float]:
    """
    설정 가능한 반복 패턴을 가진 오디오 타임라인 생성.
    
    타임라인 패턴: 
    1초 침묵 - 오디오 - 0.5초 침묵 - 오디오 - ... - 1초 침묵 (repeat_count 횟수)
    """
```

**주요 기능:**
- SRT 포맷에서 자동 타임스탬프 변환
- 5.1 오디오에서 스테레오 다운믹싱
- 원본 샘플 레이트 유지 (일반적으로 48kHz)
- TTS 동작과 일치하는 설정 가능한 반복 횟수

**사용 예시:**

```python
from langflix.audio.original_audio_extractor import OriginalAudioExtractor
from pathlib import Path

extractor = OriginalAudioExtractor("original_video.mp4")
timeline_path, duration = extractor.create_audio_timeline(
    expression,
    output_dir=Path("output/audio"),
    expression_index=0,
    audio_format="wav",
    repeat_count=3
)
```

### 타임라인 빌더 유틸리티

**위치:** `langflix/audio/timeline.py`

FFmpeg를 사용하여 반복 오디오 타임라인을 구축하는 저수준 유틸리티입니다.

**주요 함수:**

```python
def build_repeated_timeline(
    base_audio_path: Path,
    out_path: Path,
    repeat_count: int,
    start_silence: float = 1.0,
    gap_silence: float = 0.5,
    end_silence: float = 1.0,
) -> Tuple[Path, float]:
    """
    타임라인 생성: 1초 - (세그먼트 + 0.5초) * 반복횟수 - 마지막 세그먼트 - 1초.
    
    Returns (타임라인_경로, 총_길이_초).
    """
```

**주요 기능:**
- 안정적인 믹싱을 위해 모든 출력을 스테레오 48kHz로 정규화
- 효율적인 오디오 조립을 위해 FFmpeg 연결 사용
- 올바른 샘플 레이트로 자동 침묵 생성

## 구현 세부사항

### 오디오 처리 파이프라인

1. **추출**: FFmpeg를 사용하여 비디오에서 오디오 세그먼트 추출
2. **포맷 변환**: 적절한 코덱 설정으로 대상 포맷(WAV/MP3)으로 변환
3. **타임라인 생성**: 침묵 간격으로 오디오 세그먼트 연결
4. **최적화** (선택사항): 오디오 향상 적용

### FFmpeg 통합

모듈은 모든 오디오 작업에 FFmpeg를 사용:
- 오디오 추출: `ffmpeg -ss [시작] -i [비디오] -t [길이] -vn`
- 포맷 변환: `-c:a pcm_s16le` (WAV) 또는 `-c:a mp3 -b:a 192k` (MP3)
- 연결: `ffmpeg -f concat -safe 0 -i [목록]`

### 오디오 포맷 처리

- **WAV**: 16-bit PCM, 스테레오, 원본 샘플 레이트 유지
- **MP3**: 192k 비트레이트, 스테레오
- **샘플 레이트**: 48kHz 유지 (비디오 오디오의 일반적인 값)
- **채널**: 필요한 경우 5.1에서 스테레오로 다운믹싱

## 의존성

- `subprocess`: FFmpeg 명령 실행
- `pathlib`: 경로 처리
- `tempfile`: 임시 파일 관리
- `langflix.core.models`: ExpressionAnalysis 모델
- `langflix.settings`: 설정 접근

## 일반적인 작업

### 단일 표현식에 대한 오디오 추출

```python
from langflix.audio.original_audio_extractor import OriginalAudioExtractor

extractor = OriginalAudioExtractor("video.mp4")
audio_path, duration = extractor.extract_expression_audio(
    expression,
    Path("output/audio.wav"),
    audio_format="wav"
)
```

### 사용자 정의 반복 횟수로 타임라인 생성

```python
timeline_path, total_duration = extractor.create_audio_timeline(
    expression,
    output_dir=Path("output"),
    expression_index=0,
    repeat_count=5  # 5회 반복
)
```

### 오디오 품질 최적화

```python
from langflix.audio.audio_optimizer import get_audio_optimizer

optimizer = get_audio_optimizer()
metrics = optimizer.optimize_audio(
    "input.wav",
    "output.wav",
    optimization_level="high"
)

recommendations = optimizer.get_optimization_recommendations(metrics)
for rec in recommendations:
    print(f"권장사항: {rec}")
```

## 설정

오디오 설정은 `langflix.settings`를 통해 제어됩니다:

- `expression.repeat_count`: 타임라인에서 오디오 반복 횟수
- 오디오 포맷 기본 설정
- 샘플 레이트 및 채널 설정

## 주의사항

1. **샘플 레이트 일관성**: 동기화 문제를 피하기 위해 비디오 오디오는 항상 48kHz 사용
2. **침묵 생성**: 침묵 파일은 오디오 샘플 레이트와 정확히 일치해야 함
3. **FFmpeg 요구사항**: FFmpeg가 설치되어 있고 PATH에 있어야 함
4. **파일 권한**: 출력 디렉토리에 대한 쓰기 권한 확인
5. **임시 파일**: 모듈은 중간 처리를 위해 임시 디렉토리를 사용하므로 충분한 디스크 공간 필요

## 관련 모듈

- `langflix/core/`: ExpressionAnalysis 모델
- `langflix/media/`: 비디오 처리 유틸리티
- `langflix/tts/`: TTS 오디오 생성 (원본 오디오 대안)

