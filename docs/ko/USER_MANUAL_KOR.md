# LangFlix 사용자 매뉴얼

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

LangFlix에 오신 것을 환영합니다! 이 매뉴얼은 좋아하는 TV 쇼에서 영어 학습용 교육 비디오를 만드는 데 필요한 모든 것을 안내합니다.

---

## 목차

1. [소개](#소개)
2. [시작하기](#시작하기)
3. [기본 사용법](#기본-사용법)
4. [고급 사용법](#고급-사용법)
5. [설정](#설정)
6. [출력 이해하기](#출력-이해하기)
7. [명령어 참조](#명령어-참조)
8. [모범 사례](#모범-사례)
9. [문제 해결](#문제-해결)

---

## 소개

### LangFlix란?

LangFlix는 TV 쇼 자막을 자동으로 분석하여 유용한 영어 표현, 관용구, 구문을 추출한 후 다음을 포함한 교육 비디오를 생성합니다:
- 대상 언어 자막이 있는 컨텍스트 비디오 클립
- 표현 분석이 포함된 교육 슬라이드
- 3회 반복 음성 발음
- 유사 표현 및 사용 예시

### 누구를 위한 것인가요?

- 실제 미디어에서 배우고 싶은 언어 학습자
- 교육 콘텐츠를 제작하는 교사
- 언어 학습 자료를 만드는 콘텐츠 크리에이터

### 시스템 요구사항

- **Python:** 3.9 이상
- **ffmpeg:** 최신 버전 (비디오 처리용)
- **저장 공간:** 에피소드당 최소 5GB 여유 공간
- **API 키:** Google Gemini API 키 (무료 티어 사용 가능)

---

## 시작하기

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# ffmpeg 설치 (아직 설치하지 않은 경우)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg
# Windows:
choco install ffmpeg
```

### 2. 설정

```bash
# 예제 설정 파일 복사
cp config.example.yaml config.yaml

# 환경 파일 복사
cp env.example .env

# .env 파일을 편집하여 API 키 추가
# GEMINI_API_KEY=your_api_key_here
```

### 3. 미디어 파일 준비

파일을 다음 구조로 정리하세요:

```
assets/
└── media/
    └── Suits/                    # 시리즈 폴더
        ├── Suits.S01E01.720p.HDTV.x264.mkv
        ├── Suits.S01E01.720p.HDTV.x264.srt
        ├── Suits.S01E02.720p.HDTV.x264.mkv
        ├── Suits.S01E02.720p.HDTV.x264.srt
        └── ...
```

**파일 요구사항:**
- 비디오 및 자막 파일의 이름이 일치해야 함
- 지원되는 비디오 형식: `.mp4`, `.mkv`, `.avi`, `.mov`
- 자막 형식: `.srt` (UTF-8 인코딩 권장)

---

## 기본 사용법

### 빠른 시작: 에피소드 하나 처리하기

```bash
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" \
  --video-dir "assets/media"
```

이 명령은 다음을 수행합니다:
1. 자막 파일 파싱
2. AI를 사용한 표현 분석
3. 비디오 클립 추출
4. 교육 비디오 생성
5. 모든 것을 `output/` 디렉토리에 저장

### 결과 확인하기

처리 후 다음을 찾을 수 있습니다:

```
output/
└── Suits/
    └── S01E01_720p.HDTV.x264/
        ├── shared/
        │   └── video_clips/              # 원본 표현 클립
        └── translations/
            └── ko/                        # 한국어 (또는 대상 언어)
                ├── context_videos/        # 자막이 있는 컨텍스트 클립
                ├── slides/                # 교육 슬라이드
                ├── final_videos/          # 완전한 교육 시퀀스
                │   ├── educational_expression_01.mkv
                │   ├── educational_expression_02.mkv
                │   └── final_educational_video_with_slides.mkv  # 모두 결합!
                └── metadata/              # 처리 정보
```

### 테스트 모드 (첫 실행 권장)

```bash
# 설정을 테스트하기 위해 첫 번째 청크만 처리
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" \
  --video-dir "assets/media" \
  --test-mode \
  --max-expressions 2
```

---

## 고급 사용법

### 언어 레벨 선택

다양한 숙련도 수준을 대상으로 할 수 있습니다:

```bash
# 초급 수준 (간단하고 실용적인 표현)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level beginner

# 중급 수준 (균형 잡힌 복잡도)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level intermediate

# 고급 수준 (복잡한 관용구 및 구문)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level advanced

# 혼합 수준 (다양한 난이도)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level mixed
```

### 대상 언어 선택

LangFlix는 여러 대상 언어를 지원합니다:

```bash
# 한국어 (기본값)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code ko

# 일본어
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code ja

# 스페인어
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code es
```

**지원 언어:**
- `ko` - 한국어
- `ja` - 일본어
- `zh` - 중국어
- `es` - 스페인어
- `fr` - 프랑스어
- `de` - 독일어
- `pt` - 포르투갈어
- `vi` - 베트남어

### 표현 제한

청크당 추출할 표현의 수를 제어할 수 있습니다:

```bash
# 특정 수의 표현 처리
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --max-expressions 5

# 발견된 모든 표현 처리 (기본값)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt"
```

시스템은 설정에 따라 청크당 표현을 자동으로 제한합니다 (기본값: 1-3).

### 드라이 런 모드

비디오를 만들지 않고 분석을 테스트합니다:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --dry-run
```

이것은 다음을 수행합니다:
- 자막 파싱
- AI를 사용한 표현 분석
- 결과를 JSON에 저장
- 비디오 처리 **건너뛰기** (훨씬 빠름!)

### AI 출력 저장하여 검토

AI 결정을 디버그하거나 검토합니다:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --save-llm-output
```

LLM 응답은 수동 검사를 위해 `output/llm_output_*.txt`에 저장됩니다.

### 사용자 정의 출력 디렉토리

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --output-dir "custom_output"
```

### 상세 로깅

자세한 디버그 로그를 활성화합니다:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --verbose
```

---

## 설정

### YAML 설정 파일

LangFlix는 고급 설정을 위해 `config.yaml`을 사용합니다. 예제에서 복사하세요:

```bash
cp config.example.yaml config.yaml
```

### 주요 설정 섹션

#### 1. LLM 설정

```yaml
llm:
  max_input_length: 1680        # 청크당 문자 수
  target_language: "Korean"      # 기본 대상 언어
  default_language_level: "intermediate"
  temperature: 0.1               # AI 창의성 (0.0-1.0)
  top_p: 0.8                     # 샘플링 매개변수
  top_k: 40                      # 샘플링 매개변수
  max_retries: 3                 # API 재시도 횟수
  retry_backoff_seconds: 2       # 초기 재시도 지연
```

#### 2. 표현 제한

```yaml
processing:
  min_expressions_per_chunk: 1   # 청크당 최소 표현 수
  max_expressions_per_chunk: 3   # 청크당 최대 표현 수
```

#### 3. 비디오 처리

```yaml
video:
  codec: "libx264"               # 비디오 코덱
  preset: "fast"                 # 인코딩 속도/품질
  crf: 23                        # 품질 (18-28, 낮을수록 좋음)
  resolution: "1920x1080"        # 출력 해상도
  frame_rate: 23.976             # 프레임 속도
```

#### 4. 폰트 설정

```yaml
font:
  sizes:
    expression: 48               # 표현 텍스트 크기
    translation: 40              # 번역 텍스트 크기
    similar: 32                  # 유사 표현 크기
    default: 32                  # 기본 텍스트 크기
```

#### 5. 전환 효과

```yaml
transitions:
  enabled: true                  # 전환 효과 활성화/비활성화
  context_to_slide:
    type: "xfade"               # 전환 유형
    effect: "fade"              # 효과 스타일
    duration: 0.5               # 지속 시간(초)
```

#### 6. 텍스트-음성 변환 (TTS)

LangFlix는 발음 오디오 생성에 Gemini TTS를 사용합니다:

```yaml
tts:
  enabled: true                  # TTS 오디오 생성 활성화/비활성화
  provider: "google"             # TTS 제공업체 (google, lemonfox)
  repeat_count: 2                # TTS 오디오 반복 횟수
  
  google:
    language_code: "en-us"       # 오디오용 원본 언어 (영어)
    model_name: "gemini-2.5-flash-preview-tts"  # Gemini TTS 모델
    response_format: "wav"       # 오디오 포맷 (WAV)
    # SSML speaking rate 옵션: x-slow, slow, medium, fast, x-fast, 또는 백분율 like "0.8"
    speaking_rate: "slow"        # SSML 속도: 더 느리고 명확한 발음
    # SSML pitch 옵션: x-low, low, medium, high, x-high, 백분율 like "+10%", 또는 반음 like "-2st"
    pitch: "-4st"                # SSML 피치: 4 반음 낮춰서 더 자연스러운 소리
    alternate_voices:            # 표현 간 음성 교대
      - "Despina"                # 사용 가능한 Gemini 음성
      - "Puck"                   # 사용 가능한 Gemini 음성
```

**TTS 기능:**
- **음성 교대**: 구성된 음성들 간 자동 전환
- **타임라인 구조**: 1초 일시정지 - TTS - 0.5초 일시정지 - TTS - ... - 1초 일시정지 (설정 가능한 반복 횟수)
- **반복 횟수**: `repeat_count` 설정으로 조정 가능 (기본값: 2회)
- **SSML 제어**: 자연스러운 발음을 위한 직접적인 SSML 속도 및 피치 제어
- **원본 언어**: 대상 언어가 아닌 영어(원본 언어)를 오디오 생성에 사용
- **전체 대화 맥락**: 더 자연스러운 발음을 위해 완전한 대화 문장 사용

**설정 요구사항:**
- 환경 변수의 Gemini API 키: `GEMINI_API_KEY=your_key_here`
- 프로젝트 루트의 `.env` 파일에 추가

### 환경 변수

환경 변수로 설정을 재정의할 수 있습니다:

```bash
export LANGFLIX_LLM_MAX_INPUT_LENGTH=2000
export LANGFLIX_VIDEO_CRF=20
export LANGFLIX_TARGET_LANGUAGE="Japanese"
```

형식: `LANGFLIX_<섹션>_<키>=<값>`

---

## 출력 이해하기

### 출력 디렉토리 구조

```
output/
└── [시리즈]/
    └── [에피소드]/
        ├── shared/
        │   └── video_clips/              # 표현 클립 (자막 없음)
        │       ├── expression_01_[이름].mkv
        │       └── expression_02_[이름].mkv
        └── translations/
            └── [언어_코드]/
                ├── context_videos/        # 대상 언어 자막이 있는 컨텍스트
                │   ├── context_01_[이름].mkv
                │   └── context_02_[이름].mkv
                ├── slides/                # 교육 슬라이드
                │   ├── slide_01_[이름].mkv
                │   └── slide_02_[이름].mkv
                ├── subtitles/            # 이중 언어 자막 파일
                │   ├── expression_01_[이름].srt
                │   └── expression_02_[이름].srt
                ├── final_videos/         # 완전한 교육 시퀀스
                │   ├── educational_[expression_01].mkv
                │   ├── educational_[expression_02].mkv
                │   └── final_educational_video_with_slides.mkv
                └── metadata/             # 처리 메타데이터
                    └── processing_info.json
```

### 비디오 구조

각 교육 비디오는 다음 순서를 따릅니다:

1. **컨텍스트 비디오** (10-25초)
   - 대상 언어 자막이 있는 장면 컨텍스트
   - 자연스러운 대화 흐름
   - 중간에 표현이 나타남

2. **교육 슬라이드** (가변)
   - **NEW 5단계 레이아웃:**
     1. 표현 대화문 (상단, 40px) - 표현이 포함된 전체 문장
     2. 표현 (대화문 아래, 58px, 노란색 강조) - 학습할 핵심 표현/구문
     3. 표현 대화문 번역 (중간, 36px) - 전체 문장의 번역
     4. 표현 번역 (대화문 번역 아래, 48px, 노란색 강조) - 핵심 구문의 번역
     5. 유사 표현 (하단, 32px, 최대 2개) - 같은 의미의 다른 표현들
   - 오디오: 전체 대화문 + 표현 3회 반복

3. **다음 표현** (패턴 반복)

### 메타데이터 파일

`metadata/processing_info.json`에는 다음이 포함됩니다:

```json
{
  "series_name": "Suits",
  "episode_name": "S01E01_720p.HDTV.x264",
  "language_code": "ko",
  "total_expressions": 5,
  "processing_date": "2025-10-19T10:30:00",
  "expressions": [
    {
      "id": 1,
      "expression": "the ball's in your court",
      "translation": "이제 당신이 결정할 차례입니다",
      "context_start": "00:05:23,456",
      "context_end": "00:05:35,789",
      "scene_type": "confrontation"
    }
  ]
}
```

---

## 명령어 참조

### 메인 명령어

```bash
python -m langflix.main [옵션]
```

### 필수 인수

| 인수 | 설명 |
|------|------|
| `--subtitle PATH` | 자막 파일 경로 (.srt) |

### 선택적 인수

| 인수 | 기본값 | 설명 |
|------|--------|------|
| `--video-dir PATH` | `assets/media` | 비디오 파일이 포함된 디렉토리 |
| `--output-dir PATH` | `output` | 결과 출력 디렉토리 |
| `--language-code CODE` | `ko` | 대상 언어 코드 (ko, ja, es 등) |
| `--language-level LEVEL` | `intermediate` | 언어 수준 (beginner/intermediate/advanced/mixed) |
| `--max-expressions N` | None | 처리할 최대 표현 수 (None = 모두) |
| `--test-mode` | False | 테스트를 위해 첫 번째 청크만 처리 |
| `--dry-run` | False | 분석만, 비디오 처리 없음 |
| `--save-llm-output` | False | LLM 응답을 파일에 저장 |
| `--verbose` | False | 디버그 로깅 활성화 |

### 예제

```bash
# 기본 사용법
python -m langflix.main --subtitle "file.srt"

# 완전한 사용자 정의
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --video-dir "assets/media" \
  --output-dir "my_output" \
  --language-code ja \
  --language-level advanced \
  --max-expressions 10 \
  --save-llm-output \
  --verbose

# 빠른 테스트
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 2

# 분석만
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run
```

---

## 8. 숏 비디오 생성

### 개요
LangFlix는 Instagram, TikTok, YouTube Shorts와 같은 소셜 미디어 플랫폼에 최적화된 숏 포맷 비디오를 생성할 수 있습니다.

### 기능
- **세로 포맷**: 9:16 화면 비율 (1080x1920)
- **자동 배치**: 여러 표현을 ~120초 비디오로 결합
- **컨텍스트 + 교육**: 상단 절반은 컨텍스트 비디오, 하단 절반은 교육 슬라이드 표시
- **소셜 미디어 준비**: 모바일 시청 및 공유에 최적화

### 설정
```yaml
short_video:
  enabled: true                  # 숏 비디오 생성 활성화/비활성화
  resolution: "1080x1920"       # 9:16 세로 포맷
  target_duration: 120         # 배치당 목표 지속 시간 (초)
  duration_variance: 10        # ±10초 허용
```

### 사용법
```bash
# 기본: 숏 비디오 활성화
python -m langflix.main --subtitle "file.srt"

# 숏 비디오 생성 건너뛰기
python -m langflix.main --subtitle "file.srt" --no-shorts
```

### 출력 구조
```
output/Series/Episode/translations/ko/
├── context_slide_combined/     # 교육 비디오 (컨텍스트 + 슬라이드)
│   ├── educational_expression_01.mkv
│   └── educational_expression_02.mkv
└── short_videos/              # 숏 포맷 배치 비디오
    ├── batch_01_120s.mkv      # ~120초, 여러 표현
    ├── batch_02_115s.mkv
    └── batch_03_95s.mkv
```

### 비디오 레이아웃
- **상단 절반**: 대상 언어 자막이 있는 컨텍스트 비디오
- **하단 절반**: 교육 슬라이드 (오디오 없음)
- **오디오**: 컨텍스트 오디오 + TTS 오디오 (`repeat_count`에 따라 반복)
- **프리즈 프레임**: TTS 재생 중 컨텍스트 비디오가 마지막 프레임 유지

## 9. 모범 사례

### 1. 작게 시작하기

- 첫 실행에는 `--test-mode`와 `--max-expressions 2` 사용
- 전체 에피소드를 처리하기 전에 출력 품질 확인
- 다양한 언어 수준으로 테스트하여 최적 찾기

### 2. 성능 최적화

- 안정성을 위해 한 번에 하나의 에피소드 처리
- 비디오 처리 전에 `--dry-run`을 사용하여 표현 테스트
- 디스크 공간 모니터링 (비디오가 클 수 있음)

### 3. 품질 관리

- `--save-llm-output`으로 LLM 출력 검토
- 품질을 위해 처음 몇 개의 표현 확인
- 표현이 너무 쉽거나 어려우면 `language_level` 조정

### 4. 파일 정리

- 일관된 이름 지정 유지: `Series.S01E01.quality.format.ext`
- 비디오 파일 옆에 자막 저장
- 시리즈별 폴더 사용

### 5. 설정 관리

- 다양한 사용 사례에 대해 별도의 설정 파일 생성
- API 키에 환경 변수 사용 (절대 커밋하지 마세요!)
- 튜닝 후 config.yaml 백업

### 6. 리소스 관리

- 비디오 처리 중 다른 애플리케이션 닫기
- 에피소드당 5GB 이상의 여유 공간 확보
- 전체 처리 전에 `test-mode`를 사용하여 확인

---

## 문제 해결

자세한 문제 해결은 [TROUBLESHOOTING_KOR.md](TROUBLESHOOTING_KOR.md)를 참조하세요.

### 빠른 수정

**문제:** API 시간 초과 오류
```bash
# config.yaml에서 청크 크기 줄이기
llm:
  max_input_length: 1680  # 시간 초과가 지속되면 더 낮게 시도
```

**문제:** 비디오를 찾을 수 없음
```bash
# 비디오와 자막의 이름이 일치하는지 확인
# 디렉토리를 지정하려면 --video-dir 사용
python -m langflix.main --subtitle "file.srt" --video-dir "path/to/videos"
```

**문제:** 메모리 부족
```bash
# 한 번에 더 적은 표현 처리
python -m langflix.main --subtitle "file.srt" --max-expressions 5
```

**문제:** 표현 품질이 낮음
```bash
# 언어 수준 조정
python -m langflix.main --subtitle "file.srt" --language-level advanced
```

### 도움 받기

1. 자세한 해결책은 [TROUBLESHOOTING_KOR.md](TROUBLESHOOTING_KOR.md) 확인
2. `langflix.log`에서 로그 검토
3. 자세한 디버그 정보를 위해 `--verbose` 플래그 사용
4. [GitHub Issues](https://github.com/taigi0315/study_english_with_suits/issues) 확인

---

## 표현식 기반 학습 설정

LangFlix는 이제 포괄적인 설정 옵션을 통한 고급 표현식 기반 학습 기능을 지원합니다.

### 표현식 설정

표현식 설정 시스템을 통해 자막 스타일링, 비디오 재생, 레이아웃 설정을 최적의 학습 경험을 위해 커스터마이징할 수 있습니다.

#### 자막 스타일링

비디오에서 표현식이 어떻게 강조되는지 설정:

```yaml
expression:
  subtitle_styling:
    default:
      color: '#FFFFFF'
      font_family: 'Arial'
      font_size: 24
      font_weight: 'normal'
      background_color: '#000000'
      background_opacity: 0.7
      position: 'bottom'
      margin_bottom: 50
    expression_highlight:
      color: '#FFD700'
      font_weight: 'bold'
      font_size: 28
      background_color: '#1A1A1A'
      background_opacity: 0.85
      animation: 'fade_in'
      duration_ms: 300
```

#### 비디오 재생 설정

더 나은 학습을 위해 표현식이 어떻게 반복되는지 제어:

```yaml
expression:
  playback:
    expression_repeat_count: 2      # 표현식을 몇 번 반복할지
    context_play_count: 1           # 컨텍스트를 몇 번 재생할지
    repeat_delay_ms: 200             # 반복 간 지연 시간
    transition_effect: 'fade'         # 클립 간 전환 효과
    transition_duration_ms: 150     # 전환 지속 시간
```

#### 레이아웃 설정

다양한 비디오 형식에 대한 레이아웃 정의:

```yaml
expression:
  layout:
    landscape:
      resolution: [1920, 1080]
      expression_video:
        width_percent: 50
        position: 'left'
        padding: 10
      educational_slide:
        width_percent: 50
        position: 'right'
        padding: 10
    portrait:
      resolution: [1080, 1920]
      context_video:
        height_percent: 75
        position: 'top'
        padding: 5
      educational_slide:
        height_percent: 25
        position: 'bottom'
        padding: 5
```

#### LLM 설정

표현식 추출을 위한 AI 모델 설정:

```yaml
expression:
  llm:
    provider: gemini
    model: gemini-1.5-pro
    api_key: ${GEMINI_API_KEY}
    temperature: 0.7
    max_tokens: 2000
    chunk_size: 50
    overlap: 5
    max_expressions_per_chunk: 5  # 청크당 최대 표현식 수
```

#### 표현식 랭킹 설정

**Phase 2**: 어떤 표현식이 선택될지 제어하는 표현식 랭킹 시스템 설정:

```yaml
llm:
  ranking:
    difficulty_weight: 0.4           # 난이도 가중치 (0-1)
    frequency_weight: 0.3             # 빈도 가중치 (0-1)
    educational_value_weight: 0.3     # 교육적 가치 가중치 (0-1)
    fuzzy_match_threshold: 85         # 중복 감지를 위한 유사도 임계값 (0-100)
```

**랭킹 알고리즘**:
```
점수 = 난이도 × 0.4 + log(빈도) × 0.3 + 교육적_가치 × 0.3
```

**매개변수**:
- **difficulty_weight**: 도전적인 표현식의 우선순위 (기본값: 0.4)
- **frequency_weight**: 일반적인 표현식의 우선순위 (기본값: 0.3)
- **educational_value_weight**: 교육적 가치의 우선순위 (기본값: 0.3)
- **fuzzy_match_threshold**: 중복 감지를 위한 유사도 퍼센트 (기본값: 85)

**팁**:
- difficulty_weight 높임 → 더 고급 표현식
- frequency_weight 높임 → 더 일반적인 표현식
- educational_value_weight 높임 → 더 교육적으로 가치 있는 표현식
- fuzzy_match_threshold 낮춤 → 더 적극적인 중복 제거

#### WhisperX 설정

정확한 타임스탬프 감지를 위한 설정:

```yaml
expression:
  whisper:
    model_size: base
    device: cpu
    compute_type: float32
    language: null
    fuzzy_threshold: 0.85
    buffer_start: 0.2
    buffer_end: 0.2
    cache_dir: ./cache/audio
    batch_size: 16
```

### 표현식 데이터베이스 필드

시스템은 이제 각 표현식에 대한 추가 메타데이터를 추적합니다:

- **difficulty**: 1-10 난이도 수준
- **category**: 표현식 유형 (관용구, 슬랭, 격식체 등)
- **educational_value**: 이 표현식이 학습에 왜 가치 있는지
- **usage_notes**: 사용에 대한 추가 컨텍스트
- **score**: 표현식 선택을 위한 순위 점수

### 환경 변수 오버라이드

환경 변수를 사용하여 모든 설정을 오버라이드할 수 있습니다:

```bash
# 자막 스타일링 오버라이드
export LANGFLIX_EXPRESSION_SUBTITLE_STYLING_DEFAULT_COLOR="#FF0000"

# 재생 설정 오버라이드
export LANGFLIX_EXPRESSION_PLAYBACK_EXPRESSION_REPEAT_COUNT=3

# 레이아웃 해상도 오버라이드
export LANGFLIX_EXPRESSION_LAYOUT_LANDSCAPE_RESOLUTION="[2560,1440]"
```

## 다음 단계

- 프로그래밍 방식 사용을 위한 [API_REFERENCE_KOR.md](API_REFERENCE_KOR.md) 읽기
- 프로덕션 설정을 위한 [DEPLOYMENT_KOR.md](DEPLOYMENT_KOR.md) 참조
- 최적화 팁을 위한 [PERFORMANCE_KOR.md](PERFORMANCE_KOR.md) 확인
- 일반적인 문제를 위한 [TROUBLESHOOTING_KOR.md](TROUBLESHOOTING_KOR.md) 검토

---

**즐거운 학습 되세요! 🎓**

*이 매뉴얼의 영어 버전은 [USER_MANUAL.md](USER_MANUAL.md)를 참조하세요*

