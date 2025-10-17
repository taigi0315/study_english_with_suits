# LangFlix Setup Guide

## 프로젝트 개요 (Project Overview)

LangFlix는 TV 쇼의 자막을 분석하여 영어 표현 학습용 비디오를 자동 생성하는 도구입니다.

## 설치 방법 (Installation)

### 1. 가상환경 설정
```bash
# 가상환경 생성 (이미 생성되어 있다면 생략)
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
```bash
# .env 파일 생성
cp env.example .env

# .env 파일을 편집하여 API 키 설정
# GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Gemini API 키 발급
1. [Google AI Studio](https://aistudio.google.com/) 방문
2. Google 계정으로 로그인
3. API 키 생성
4. `.env` 파일에 `GEMINI_API_KEY` 설정

## 테스트 실행 (Running Tests)

```bash
# 단위 테스트 실행
python -m pytest tests/

# 특정 테스트 파일 실행
python -m pytest tests/test_expression_analyzer.py -v
```

## 사용 방법 (Usage)

### 1. 자막 파일 준비
- `.srt` 형식의 자막 파일 필요
- 예시: `assets/subtitles/Suits - season 1.en/` 폴더의 파일들

### 2. 기본 실행
```bash
python -m langflix.main --subtitle path/to/subtitle.srt --video path/to/video.mp4
```

### 3. 드라이 런 (JSON만 생성, 비디오 처리 없음)
```bash
python -m langflix.main --subtitle path/to/subtitle.srt --dry-run
```

## 개발 상태 (Development Status)

- ✅ **Phase 1**: 핵심 로직 및 콘텐츠 생성
  - ✅ 자막 파서 구현
  - ✅ 표현 분석기 구현 (Gemini API 연동)
  - ✅ 프롬프트 엔지니어링
  - ✅ 에러 처리 및 로깅

- 🔄 **Phase 2**: 비디오 처리 및 조립 (진행 예정)
  - 비디오 클립 추출
  - 제목 카드 생성
  - 최종 비디오 조립

- 📋 **Phase 3**: 개선 및 사용성 (계획)
  - CLI 개선
  - 로깅 및 오류 보고
  - 문서화

## 문제 해결 (Troubleshooting)

### API 키 오류
```
Error: GEMINI_API_KEY not found
```
→ `.env` 파일에 올바른 API 키가 설정되어 있는지 확인

### JSON 파싱 오류
```
Error parsing JSON from LLM response
```
→ Gemini API 응답이 올바른 JSON 형식이 아닐 수 있음. 로그를 확인하여 원본 응답 확인

### 의존성 오류
```
Import "google.generativeai" could not be resolved
```
→ `pip install -r requirements.txt` 실행하여 의존성 재설치
