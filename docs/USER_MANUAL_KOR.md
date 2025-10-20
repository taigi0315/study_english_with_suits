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

LangFlix는 발음 오디오 생성에 Google Cloud Text-to-Speech를 사용합니다:

```yaml
tts:
  enabled: true                  # TTS 오디오 생성 활성화/비활성화
  provider: "google"             # TTS 제공업체 (google, lemonfox)
  
  google:
    language_code: "en-US"       # 오디오용 원본 언어 (영어)
    voice_name: "en-US-Wavenet-D" # 기본 음성 (Puck)
    response_format: "mp3"       # 오디오 포맷 (mp3, wav)
    speaking_rate: 0.75          # 말하기 속도 (0.75 = 75% 속도, 느림)
    alternate_voices:            # 표현 간 음성 교대
      - "en-US-Wavenet-D"        # Puck (남성, 중립적 톤)
      - "en-US-Wavenet-A"        # Leda (여성, 중립적 톤)
```

**TTS 기능:**
- **음성 교대**: 각 표현마다 Puck과 Leda 음성 자동 전환
- **타임라인 구조**: 1초 일시정지 - TTS - 0.5초 일시정지 - TTS - 0.5초 일시정지 - TTS - 1초 일시정지
- **말하기 속도**: 더 나은 학습을 위한 설정 가능한 느린 말하기 (75% 속도)
- **원본 언어**: 대상 언어가 아닌 영어(원본 언어)를 오디오 생성에 사용

**설정 요구사항:**
- 환경 변수의 Google Cloud TTS API 키: `GOOGLE_API_KEY_1=your_key_here`
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
   - 영어 표현 (상단, 48px)
   - 번역 (중간, 40px)
   - 유사 표현 (하단, 32px, 최대 2개)
   - 오디오: 표현 3회 반복

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

## 모범 사례

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

## 다음 단계

- 프로그래밍 방식 사용을 위한 [API_REFERENCE_KOR.md](API_REFERENCE_KOR.md) 읽기
- 프로덕션 설정을 위한 [DEPLOYMENT_KOR.md](DEPLOYMENT_KOR.md) 참조
- 최적화 팁을 위한 [PERFORMANCE_KOR.md](PERFORMANCE_KOR.md) 확인
- 일반적인 문제를 위한 [TROUBLESHOOTING_KOR.md](TROUBLESHOOTING_KOR.md) 검토

---

**즐거운 학습 되세요! 🎓**

*이 매뉴얼의 영어 버전은 [USER_MANUAL.md](USER_MANUAL.md)를 참조하세요*

