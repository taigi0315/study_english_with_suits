# LangFlix 문제 해결 가이드

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

이 가이드는 LangFlix 사용 중 발생하는 일반적인 문제를 진단하고 해결하는 데 도움을 드립니다.

---

## 목차

1. [설치 문제](#설치-문제)
2. [API 및 LLM 문제](#api-및-llm-문제)
3. [TTS (텍스트-음성 변환) 문제](#tts-텍스트-음성-변환-문제)
4. [비디오 처리 문제](#비디오-처리-문제)
5. [자막 처리 문제](#자막-처리-문제)
6. [성능 및 리소스 문제](#성능-및-리소스-문제)
7. [출력 및 품질 문제](#출력-및-품질-문제)
8. [설정 문제](#설정-문제)
9. [디버깅 팁](#디버깅-팁)
10. [에러 메시지 참조](#에러-메시지-참조)
11. [자주 묻는 질문](#자주-묻는-질문)

---

## 설치 문제

### 문제: "ModuleNotFoundError: No module named 'langflix'"

**증상:**
```
ModuleNotFoundError: No module named 'langflix'
```

**해결 방법:**
1. 가상 환경이 활성화되어 있는지 확인:
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. 프로젝트 루트 디렉토리에서 실행:
   ```bash
   cd /path/to/study_english_with_sutis
   python -m langflix.main --subtitle "file.srt"
   ```

---

### 문제: "ffmpeg: command not found"

**증상:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**해결 방법:**

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
```bash
# Chocolatey 사용
choco install ffmpeg

# 또는 https://ffmpeg.org/download.html 에서 직접 다운로드
# PATH에 수동으로 추가
```

**설치 확인:**
```bash
ffmpeg -version
```

---

### 문제: "GEMINI_API_KEY not found"

**증상:**
```
Error: GEMINI_API_KEY environment variable not set
```

**해결 방법:**

1. `.env` 파일 생성:
   ```bash
   cp env.example .env
   ```

2. `.env` 파일을 편집하여 API 키 추가:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. API 키 얻기:
   - https://aistudio.google.com/
   - Google 계정으로 로그인
   - 새 API 키 생성

4. `.env`가 프로젝트 루트 디렉토리에 있는지 확인

---

## API 및 LLM 문제

### 문제: API 타임아웃 (504 Gateway Timeout)

**증상:**
```
Error: 504 Gateway Timeout
Gemini API request timed out
```

**원인:**
- 입력 청크가 너무 큼
- 네트워크 연결 문제
- API 서버 과부하

**해결 방법:**

1. **`config.yaml`에서 청크 크기 줄이기:**
   ```yaml
   llm:
     max_input_length: 1680  # 더 낮은 값 시도: 1200, 800
   ```

2. **재시도 로직 활성화 (자동으로 활성화됨):**
   ```yaml
   llm:
     max_retries: 3
     retry_backoff_seconds: 2
   ```

3. **더 작은 입력으로 테스트:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --max-expressions 1
   ```

4. **네트워크 연결 확인:**
   ```bash
   ping google.com
   curl https://generativelanguage.googleapis.com
   ```

---

### 문제: "MAX_TOKENS" 완료 이유

**증상:**
```
Warning: LLM response ended with MAX_TOKENS
Response may be incomplete
```

**원인:**
- 출력이 토큰 제한을 초과
- 너무 많은 표현 요청
- 복잡한 프롬프트로 더 많은 토큰 필요

**해결 방법:**

1. **청크당 표현 수 줄이기:**
   ```yaml
   processing:
     max_expressions_per_chunk: 2  # 1 또는 2로 시도
   ```

2. **프롬프트 단순화** (`langflix/templates/expression_analysis_prompt.txt` 편집)

3. **청크당 자막 수 줄이기:**
   ```yaml
   llm:
     max_input_length: 1200  # 1680에서 줄이기
   ```

---

### 문제: 빈 또는 잘못된 JSON 응답

**증상:**
```
Error: Failed to parse JSON from LLM response
JSONDecodeError: Expecting value
```

**원인:**
- API가 JSON이 아닌 텍스트 반환
- 응답이 잘림
- 모델 환각

**해결 방법:**

1. **LLM 출력 저장하여 검사:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --save-llm-output
   ```
   `output/llm_output_*.txt`에서 실제 응답 확인

2. **다른 매개변수로 재시도:**
   ```yaml
   llm:
     temperature: 0.1  # 낮은 온도 = 더 일관성
     top_p: 0.8
     top_k: 40
   ```

3. **문제 격리를 위해 테스트 모드 사용:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --dry-run
   ```

---

### 문제: API 속도 제한 / 할당량 초과

**증상:**
```
Error: 429 Too Many Requests
Quota exceeded for metric
```

**해결 방법:**

1. **API 할당량 확인:**
   - https://console.cloud.google.com/ 방문
   - Gemini API 사용량 및 제한 확인

2. **요청 간 지연 추가:**
   ```yaml
   llm:
     retry_backoff_seconds: 5  # 지연 시간 증가
   ```

3. **한 번에 더 적은 표현 처리:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --max-expressions 3
   ```

4. **무료 티어를 많이 사용하는 경우 API 플랜 업그레이드**

---

## TTS (텍스트-음성 변환) 문제

### 문제: "Google Cloud API 키가 필요합니다"

**증상:**
```
Error: Google Cloud API key is required. Set GOOGLE_API_KEY environment variable
```

**해결 방법:**
1. **`.env` 파일에 API 키 추가:**
   ```bash
   GOOGLE_API_KEY_1=your_google_cloud_api_key_here
   ```

2. **키가 로드되었는지 확인:**
   ```bash
   cat .env | grep GOOGLE_API_KEY
   ```

3. **API 키 테스트:**
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('GOOGLE_API_KEY_1')[:10] + '...' if os.getenv('GOOGLE_API_KEY_1') else 'Not found')"
   ```

### 문제: "TTS 오디오 생성 또는 재생 안됨"

**증상:**
- 교육 슬라이드에 오디오 없음
- 무음 파일 생성됨
- 오디오 파일 생성되었지만 비어있거나 재생 안됨

**해결 방법:**
1. **`default.yaml`에서 TTS 설정 확인:**
   ```yaml
   tts:
     enabled: true
     provider: "google"
     google:
       language_code: "en-US"
       response_format: "mp3"
   ```

2. **API 키 형식 확인:**
   - Google Cloud API 키는 `AIza`로 시작해야 함
   - `.env` 파일에서 키 주변에 따옴표나 공백 없음

3. **TTS 직접 테스트:**
   ```bash
   python tests/test_tts_integration.py
   ```

4. **로그에서 TTS 에러 확인:**
   ```bash
   python -m langflix.main --verbose --test-mode
   ```

### 문제: "ModuleNotFoundError: No module named 'google.cloud'"

**증상:**
```
ModuleNotFoundError: No module named 'google.cloud'
```

**해결 방법:**
```bash
pip install google-cloud-texttospeech>=2.16.0
```

### 문제: TTS 오디오 품질 문제

**증상:**
- 오디오가 너무 빠르거나 느림
- 발음이 불분명함
- 잘못된 음성 사용됨

**해결 방법:**
1. **설정에서 말하기 속도 조정:**
   ```yaml
   tts:
     google:
       speaking_rate: 0.75  # 75% 속도 (느림)
   ```

2. **음성 변경:**
   ```yaml
   tts:
     google:
       voice_name: "en-US-Wavenet-A"  # 다른 음성 시도
       alternate_voices: ["en-US-Wavenet-A", "en-US-Wavenet-D"]
   ```

3. **텍스트 정리 확인:**
   - 표현 텍스트가 깔끔한 영어여야 함
   - 특수 문자나 기호 없음

---

## 비디오 처리 문제

### 문제: "비디오 파일을 찾을 수 없음"

**증상:**
```
Error: Could not find video file for subtitle
Searched: [경로 목록]
```

**해결 방법:**

1. **비디오와 자막의 이름이 일치하는지 확인:**
   ```
   ✓ Suits.S01E01.720p.HDTV.x264.mkv
   ✓ Suits.S01E01.720p.HDTV.x264.srt
   
   ✗ Suits_S01E01.mkv
   ✗ Suits.S01E01.srt  (이름 형식이 다름)
   ```

2. **비디오 디렉토리를 명시적으로 지정:**
   ```bash
   python -m langflix.main \
     --subtitle "path/to/subtitle.srt" \
     --video-dir "path/to/videos"
   ```

3. **파일 권한 확인:**
   ```bash
   ls -la path/to/video/file.mkv
   chmod 644 path/to/video/file.mkv  # 필요한 경우
   ```

---

### 문제: FFmpeg 인코딩 오류

**증상:**
```
Error: ffmpeg returned non-zero exit code
Error processing video: codec not supported
```

**해결 방법:**

1. **비디오 코덱 호환성 확인:**
   ```bash
   ffmpeg -i input_video.mkv
   # 비디오 코덱 확인 (h264, hevc 등)
   ```

2. **문제가 있는 비디오 재인코딩:**
   ```bash
   ffmpeg -i problematic.mkv -c:v libx264 -c:a aac fixed.mkv
   ```

3. **ffmpeg을 최신 버전으로 업데이트:**
   ```bash
   # macOS
   brew upgrade ffmpeg
   
   # Ubuntu
   sudo apt update && sudo apt upgrade ffmpeg
   ```

4. **비디오 파일 무결성 확인:**
   ```bash
   ffmpeg -v error -i video.mkv -f null -
   ```

---

### 문제: 비디오/오디오 동기화 문제

**증상:**
- 오디오가 비디오와 맞지 않음
- 자막이 잘못된 시간에 나타남
- 표현 타이밍이 어긋남

**해결 방법:**

1. **자막 타이밍 확인:**
   - 텍스트 편집기에서 자막 파일 열기
   - 타임스탬프가 비디오 재생과 일치하는지 확인

2. **정확한 타이밍으로 재추출:**
   ```yaml
   video:
     frame_rate: 23.976  # 원본 비디오와 정확히 일치
   ```

3. **가변 프레임률(VFR) 확인:**
   ```bash
   ffmpeg -i video.mkv
   # "Variable frame rate" 경고 확인
   
   # 필요한 경우 VFR을 CFR로 변환:
   ffmpeg -i input.mkv -vsync cfr -r 23.976 output.mkv
   ```

---

### 문제: 비디오 처리 중 "메모리 부족"

**증상:**
```
MemoryError: Unable to allocate memory
Killed (signal 9)
```

**해결 방법:**

1. **한 번에 더 적은 표현 처리:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --max-expressions 3
   ```

2. **비디오 해상도 낮추기:**
   ```yaml
   video:
     resolution: "1280x720"  # 1920x1080 대신
     crf: 25  # 더 높은 CRF = 더 작은 파일
   ```

3. **다른 애플리케이션 종료** 후 처리

4. **사용 가능한 메모리 확인:**
   ```bash
   # macOS/Linux
   free -h
   
   # macOS
   vm_stat
   ```

5. **스왑 공간 활성화** (Linux):
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## 자막 처리 문제

### 문제: "자막 인코딩 오류"

**증상:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
Invalid subtitle format
```

**해결 방법:**

1. **자막을 UTF-8로 변환:**
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt
   ```

2. **자막 인코딩 확인:**
   ```bash
   file -i subtitle.srt
   ```

3. **자막 편집기로 수정:**
   - Subtitle Edit (Windows)
   - Aegisub (크로스 플랫폼)
   - UTF-8 인코딩으로 저장

---

### 문제: "표현에 대한 일치하는 자막을 찾을 수 없음"

**증상:**
```
Warning: Could not find subtitle timing for expression
Skipping expression: [표현 텍스트]
```

**해결 방법:**

1. **자막 파일 완전성 확인:**
   - 자막이 전체 비디오 지속 시간을 커버하는지 확인
   - 타이밍에 큰 간격이 없는지 확인

2. **표현 텍스트가 자막과 일치하는지 확인:**
   - LLM이 표현 텍스트를 수정했을 수 있음
   - `--save-llm-output`로 확인

3. **매칭 허용 오차 조정** (코드 수정 필요):
   ```python
   # subtitle_processor.py에서
   # 퍼지 매칭 임계값 증가
   ```

---

### 문제: 출력 비디오에서 "번역 누락"

**증상:**
- 교육 슬라이드에 "[translation missing]" 표시
- 이중 언어 자막 불완전

**원인:**
- LLM이 모든 대화에 번역을 제공하지 않음
- 대화/번역 배열 불일치

**해결 방법:**

1. **시스템이 자동으로 이를 검증함** - 불일치하는 번역이 있는 표현은 필터링됨

2. **LLM 출력 확인:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --save-llm-output
   ```
   `llm_output_*.txt`에서 대화/번역 개수 확인

3. **필요한 경우 프롬프트 조정** (`langflix/templates/expression_analysis_prompt.txt` 편집)

---

### 문제: 일부 컨텍스트 비디오에서 자막이 표시되지 않음

**증상:**
- 일부 컨텍스트 비디오에서 자막이 표시되지 않지만 다른 비디오는 정상 표시
- `translations/{lang}/subtitles/` 디렉토리에 자막 파일이 존재함
- 오류 로그에서 "Could not find subtitle file for expression" 표시

**원인:**
- 파일명 잘림으로 인한 자막 파일명 불일치
- 표현 텍스트가 파일명 허용 길이보다 김 (예: `get_to_someone_through_someone_else`가 `expression_01_get_to_someone_through_someone.srt`로 됨)

**해결 방법:**

1. **시스템이 자동으로 처리함** - LangFlix는 파일명이 잘려도 스마트 부분 매칭을 사용하여 자막 파일을 찾음

2. **문제가 지속되면 자막 파일 매칭 확인:**
   ```bash
   # 사용 가능한 자막 파일 확인
   ls -la output/Series/Episode/translations/{lang}/subtitles/
   
   # 파일명 패턴이 표현과 일치하는지 확인
   # 패턴: expression_XX_{expression_text}.srt
   ```

3. **디버깅을 위해 상세 로깅 활성화:**
   이런 로그 메시지를 찾아보세요:
   ```
   INFO | Looking for subtitle files in: {directory}
   INFO | Available subtitle files: [...]
   INFO | Found potential match via partial matching: {file_path}
   ```

**기술적 세부사항:**
시스템은 여러 매칭 전략을 사용합니다:
- 표현 텍스트와 정확한 매칭
- 잘린 파일명에 대한 부분 매칭
- 인덱스 접두사와 패턴 매칭 (expression_01_, expression_02_ 등)

---

## 성능 및 리소스 문제

### 문제: 처리 속도가 매우 느림

**증상:**
- 에피소드 하나 처리에 몇 시간 소요
- CPU 사용률이 지속적으로 높음

**해결 방법:**

1. **먼저 테스트 모드 사용:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --max-expressions 2
   ```

2. **비디오 인코딩 최적화:**
   ```yaml
   video:
     preset: "ultrafast"  # 더 빠른 인코딩, 더 큰 파일
     # 또는: "fast", "medium", "slow"
   ```

3. **비디오 품질 낮추기:**
   ```yaml
   video:
     crf: 28  # 더 높음 = 더 빠른 인코딩 (18-28)
     resolution: "1280x720"
   ```

4. **배치로 처리:**
   - 한 번에 5-10개 표현 처리
   - 메모리 누적 방지

---

### 문제: 디스크 공간 부족

**증상:**
```
OSError: [Errno 28] No space left on device
```

**해결 방법:**

1. **사용 가능한 공간 확인:**
   ```bash
   df -h
   ```

2. **임시 파일 정리:**
   ```bash
   # 이전 출력 제거
   rm -rf output/old_series/
   
   # 테스트 출력 정리
   rm -rf test_output/
   ```

3. **비디오 압축 조정:**
   ```yaml
   video:
     crf: 25  # 더 높음 = 더 작은 파일
   ```

4. **한 번에 하나씩 에피소드 처리**하고 완료된 비디오 보관

---

## 출력 및 품질 문제

### 문제: 표현 품질이 낮음

**증상:**
- 표현이 너무 기본적/고급적
- 실용적이지 않거나 유용하지 않음
- 너무 많은 지루한 대화

**해결 방법:**

1. **언어 수준 조정:**
   ```bash
   # 더 고급 표현을 위해
   python -m langflix.main \
     --subtitle "file.srt" \
     --language-level advanced
   ```

2. **표현 제한 수정:**
   ```yaml
   processing:
     min_expressions_per_chunk: 2
     max_expressions_per_chunk: 3  # 더 선택적으로 만들기
   ```

3. **프롬프트 템플릿 사용자 정의:**
   - `langflix/templates/expression_analysis_prompt.txt` 편집
   - 선택 기준 조정
   - 특정 요구사항 추가

---

### 문제: 교육 슬라이드 텍스트가 잘림

**증상:**
- 긴 표현이 슬라이드에 맞지 않음
- 텍스트가 단어 중간에 잘림

**해결 방법:**

1. **`config.yaml`에서 폰트 크기 조정:**
   ```yaml
   font:
     sizes:
       expression: 42  # 48에서 줄이기
       translation: 36  # 40에서 줄이기
   ```

2. **텍스트 길이 제한이 `video_editor.py`에 설정됨:**
   - 표현: 최대 200자
   - 번역: 최대 200자
   - 유사: 최대 100자

3. **프롬프트 조정으로 더 짧은 표현 사용**

---

### 문제: 오디오 품질이 나쁨

**증상:**
- 깨지는 소리나 왜곡
- 볼륨이 너무 낮음/높음
- 오디오 동기화 문제

**해결 방법:**

1. **소스 비디오 오디오 확인:**
   ```bash
   ffmpeg -i video.mkv
   # 오디오 코덱과 비트레이트 확인
   ```

2. **`config.yaml`에서 오디오 설정:**
   ```yaml
   audio:
     codec: "aac"
     bitrate: "192k"
     sample_rate: 48000
   ```

3. **오디오 정규화로 재추출:**
   - 시스템이 자동으로 오디오 정규화
   - 오류에 대한 ffmpeg 로그 확인

---

## 설정 문제

### 문제: 설정 파일이 로드되지 않음

**증상:**
```
Warning: Could not load config.yaml
Using default settings
```

**해결 방법:**

1. **프로젝트 루트에 `config.yaml`이 있는지 확인:**
   ```bash
   ls -la config.yaml
   ```

2. **예제에서 복사:**
   ```bash
   cp config.example.yaml config.yaml
   ```

3. **YAML 구문 확인:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

4. **yamllint로 검증:**
   ```bash
   pip install yamllint
   yamllint config.yaml
   ```

---

### 문제: 환경 변수가 작동하지 않음

**증상:**
- `.env` 파일 변경사항이 적용되지 않음
- API 키가 인식되지 않음

**해결 방법:**

1. **`.env` 파일이 프로젝트 루트에 있는지 확인:**
   ```bash
   ls -la .env
   ```

2. **`.env`에서 `=` 주변에 공백 없이:**
   ```
   # 올바른 형식:
   GEMINI_API_KEY=abc123
   
   # 잘못된 형식:
   GEMINI_API_KEY = abc123
   ```

3. **`.env` 편집 후 터미널/셸 재시작**

4. **변수가 설정되었는지 확인:**
   ```bash
   echo $GEMINI_API_KEY
   ```

---

## 디버깅 팁

### 상세 로깅 활성화

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --verbose
```

이것은 다음을 제공합니다:
- 상세한 함수 호출 추적
- 매개변수 값
- 타이밍 정보
- 오류 컨텍스트

### 로그 파일 확인

```bash
# 메인 로그 보기
tail -f langflix.log

# 오류 검색
grep "ERROR" langflix.log
grep "Exception" langflix.log
```

### 드라이 런 모드 사용

```bash
# 비디오 처리 없이 테스트
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run
```

장점:
- 훨씬 빠름
- LLM 통합만 테스트
- 설정 문제 식별
- 비디오 저장소 불필요

### LLM 출력 저장

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output
```

`output/llm_output_*.txt`를 검사하여 다음 확인:
- LLM에 보낸 정확한 프롬프트
- 원시 LLM 응답
- 표현 분석 결정

### 개별 단계 테스트

단계별 테스트 시스템 사용:

```bash
# 각 단계를 독립적으로 테스트
cd tests/step_by_step

python test_step1_load_and_analyze.py
python test_step2_slice_video.py
python test_step3_add_subtitles.py
python test_step4_extract_audio.py
python test_step5_create_slide.py
```

자세한 내용은 `tests/step_by_step/README.md` 참조.

### 비디오 파일 무결성 확인

```bash
# 오류 확인
ffmpeg -v error -i video.mkv -f null -

# 상세 정보 얻기
ffprobe -v quiet -print_format json -show_format -show_streams video.mkv
```

### Python 환경 확인

```bash
# Python 버전 확인
python --version  # 3.9+이어야 함

# 설치된 패키지 확인
pip list | grep -E "(pysrt|ffmpeg|openai|pydantic)"

# langflix 패키지 확인
python -c "import langflix; print(langflix.__file__)"
```

---

## 에러 메시지 참조

### 일반적인 에러 패턴

| 에러 메시지 | 가능한 원인 | 해결 방법 섹션 |
|------------|------------|----------------|
| `ModuleNotFoundError` | 누락된 의존성 | [설치 문제](#설치-문제) |
| `GEMINI_API_KEY not found` | API 키 미설정 | [설치 문제](#설치-문제) |
| `504 Gateway Timeout` | API 타임아웃 | [API 및 LLM 문제](#api-및-llm-문제) |
| `MAX_TOKENS` | 응답 너무 긺 | [API 및 LLM 문제](#api-및-llm-문제) |
| `Video file not found` | 파일 매핑 문제 | [비디오 처리 문제](#비디오-처리-문제) |
| `ffmpeg returned non-zero` | 비디오 인코딩 오류 | [비디오 처리 문제](#비디오-처리-문제) |
| `MemoryError` | 메모리 부족 | [비디오 처리 문제](#비디오-처리-문제) |
| `UnicodeDecodeError` | 자막 인코딩 | [자막 처리 문제](#자막-처리-문제) |
| `No space left on device` | 디스크 가득참 | [성능 문제](#성능-및-리소스-문제) |
| `JSONDecodeError` | 잘못된 LLM 응답 | [API 및 LLM 문제](#api-및-llm-문제) |

---

## 자주 묻는 질문

### Q: 처리 시간은 얼마나 걸리나요?

**A:** 에피소드 길이와 시스템에 따라 다름:
- **테스트 모드 (2개 표현):** 2-5분
- **전체 에피소드 (10-20개 표현):** 20-60분
- **제한 요인:** 비디오 인코딩 시간

### Q: 여러 에피소드를 병렬로 처리할 수 있나요?

**A:** 권장하지 않음:
- 높은 메모리 사용량
- API 속도 제한
- 파일 시스템 경합
- 순차적으로 처리하는 것이 더 좋음

### Q: API 비용은 얼마나 드나요?

**A:** Gemini API:
- 무료 티어: 개인 사용에 관대한 제한
- 현재 가격 확인: https://ai.google.dev/pricing
- LangFlix는 비용을 최소화하기 위해 청크 크기를 최적화

### Q: 다른 LLM을 사용할 수 있나요?

**A:** 현재는 Gemini만 지원하지만:
- 아키텍처가 LLM 교체를 허용
- 코드 수정 필요
- `langflix/expression_analyzer.py` 참조

### Q: 표현 품질을 어떻게 개선하나요?

**A:**
1. `language_level` 매개변수 조정
2. `langflix/templates/`에서 프롬프트 템플릿 수정
3. `min_expressions_per_chunk`와 `max_expressions_per_chunk` 변경
4. `--save-llm-output`로 결정 검토

### Q: 교육 슬라이드 디자인을 사용자 정의할 수 있나요?

**A:** 네:
- 배경 이미지 편집: `assets/education_slide_background.png`
- `config.yaml`에서 폰트 크기 조정
- `video_editor.py`에서 레이아웃 수정 (코드 변경 필요)

### Q: 임시 파일은 어디에 저장되나요?

**A:**
- 임시 비디오 클립: 자동으로 정리됨
- 출력 비디오: `output/[시리즈]/[에피소드]/`
- LLM 출력: `output/llm_output_*.txt` (활성화된 경우)
- 로그: `langflix.log`

### Q: LangFlix는 어떻게 업데이트하나요?

**A:**
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Q: 비영어 자막을 처리할 수 있나요?

**A:**
- 현재 영어 학습에 최적화됨
- 소스 자막은 영어여야 함
- 대상 번역은 여러 언어 가능

---

## 추가 도움 받기

여기에서 다룬 문제가 아닌 경우:

1. **로그 확인:** `langflix.log` 및 콘솔 출력
2. **상세 모드 활성화:** `--verbose` 플래그
3. **GitHub Issues 검색:** https://github.com/taigi0315/study_english_with_suits/issues
4. **새 이슈 생성** 시 다음 포함:
   - 에러 메시지 (전체 스택 추적)
   - 실행한 명령어
   - 설정 파일 (API 키 제거!)
   - 로그 출력
   - 시스템 정보 (OS, Python 버전)

---

**더 많은 도움이 필요하신가요?** 자세한 사용 지침은 [USER_MANUAL_KOR.md](USER_MANUAL_KOR.md)를 참조하세요.

*영어 버전은 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)를 참조하세요*
