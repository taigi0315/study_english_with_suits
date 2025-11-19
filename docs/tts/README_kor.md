# TTS 모듈

## 개요

`langflix/tts/` 모듈은 여러 제공업체를 지원하는 교체 가능한 텍스트-음성(TTS) 아키텍처를 제공합니다. Google Gemini TTS 및 LemonFox TTS 지원과 함께 텍스트에서 음성 오디오를 생성하기 위한 통합 인터페이스를 제공합니다.

**목적:**
- 표현식 텍스트에서 음성 오디오 생성
- 여러 TTS 제공업체 지원 (Gemini, LemonFox)
- 제공업체 간 일관된 인터페이스 제공
- 자연스러운 음성을 위한 SSML 구성 처리
- 여러 표현식에 대한 음성 교대 지원

**사용 시기:**
- 표현식에 대한 TTS 오디오를 생성할 때
- TTS 제공업체 간 전환할 때
- 음성 설정 및 SSML 매개변수를 사용자 정의할 때
- 음성 교대 로직을 구현할 때

## 파일 목록

### `base.py`
TTS 클라이언트용 추상 기본 클래스입니다.

### `factory.py`
TTS 클라이언트 인스턴스를 생성하는 팩토리 함수입니다.

**지원되는 제공업체:**
- `google` - Google Gemini TTS
- `lemonfox` - LemonFox TTS

### `gemini_client.py`
Google Gemini TTS 클라이언트 구현입니다.

**기능:**
- 음성 제어를 위한 SSML 지원
- 여러 음성 옵션
- 구성 가능한 말하기 속도 및 피치
- 언어 코드 지원

### `lemonfox_client.py`
LemonFox TTS 클라이언트 구현입니다.

## 주요 구성 요소

### TTSClient 기본 클래스

모든 TTS 제공업체의 추상 기본 클래스입니다.

### 팩토리 패턴

모듈은 TTS 클라이언트를 생성하기 위해 팩토리 패턴을 사용합니다.

### Gemini TTS 클라이언트

Google Gemini TTS 클라이언트입니다.

**SSML 지원:**
- 말하기 속도 제어
- 피치 조정
- 음성 선택
- 언어별 설정

## 구현 세부사항

### 텍스트 정리

모든 TTS 클라이언트는 합성 전에 텍스트를 정리합니다.

### 구성 검증

각 클라이언트는 구성을 검증합니다.

### 음성 교대

시스템은 여러 표현식에 대한 음성 교대를 지원합니다.

## 의존성

**환경 변수:**
- `GEMINI_API_KEY` - Gemini API 키 (Gemini TTS용)
- `LEMONFOX_API_KEY` - LemonFox API 키 (LemonFox TTS용)

## 일반적인 작업

### Gemini TTS 사용

```python
from langflix.tts.factory import create_tts_client

config = {
    'api_key': os.getenv('GEMINI_API_KEY'),
    'voice_name': 'Kore',
    'language_code': 'en-us',
    'speaking_rate': 'medium',
    'pitch': 0.0
}

client = create_tts_client('google', config)
audio_path = client.generate_speech("break the ice")
```

## 주의사항 및 참고사항

### 중요 고려사항

1. **API 키:**
   - Gemini: `GEMINI_API_KEY` 환경 변수 설정
   - LemonFox: `LEMONFOX_API_KEY` 환경 변수 설정
   - 클라이언트 생성에 키가 필요합니다

2. **언어 코드:**
   - Gemini는 소문자 형식 사용: `en-us`, `ko-kr`
   - 기본값: 영어의 경우 `en-us`

3. **음성 선택:**
   - Gemini: `Kore` (기본값), `Charon` 등
   - LemonFox: `bella` 및 기타 음성
   - 음성 가용성은 제공업체에 따라 다릅니다

## 관련 문서

- [Core Module](../core/README_eng.md) - TTS를 사용하는 표현식 처리
- [Audio Module](../audio/README_eng.md) - 오디오 처리 및 최적화
- [Config Module](../config/README_eng.md) - TTS 설정

