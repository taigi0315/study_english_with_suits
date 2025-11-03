# YouTube OAuth Credentials 설정 가이드

## ⚠️ 중요: API Key와 OAuth 자격 증명의 차이

제공해주신 `AIzaSyCtp24uebNtFrTEsH4scaLGcYUkP-TkylE`는 **Google API Key**입니다.
YouTube 로그인 기능을 사용하려면 **OAuth 2.0 Client ID와 Client Secret**이 필요합니다.

이것들은 서로 다른 것입니다:
- **API Key**: 특정 API 호출에 사용 (예: YouTube Data API 조회)
- **OAuth 2.0 Credentials**: 사용자 인증에 사용 (로그인)

## 📋 OAuth 2.0 자격 증명 생성 방법

### Step 1: Google Cloud Console 접속
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 선택 (또는 새로 생성)

### Step 2: YouTube Data API v3 활성화
1. "APIs & Services" → "Library"로 이동
2. "YouTube Data API v3" 검색 후 "Enable" 클릭

### Step 3: OAuth 2.0 클라이언트 ID 생성
1. "APIs & Services" → "Credentials"로 이동
2. "+ CREATE CREDENTIALS" → "OAuth client ID" 선택
3. 처음이면 OAuth 동의 화면 설정:
   - User Type: "External" 선택 (개인 사용)
   - 앱 정보 입력 (앱 이름, 사용자 지원 이메일 등)
   - Scopes: 기본값 사용
   - 테스트 사용자에 본인 이메일 추가
4. OAuth 클라이언트 ID 생성:
   - Application type: **"Desktop app"** 선택
   - Name: "LangFlix YouTube Uploader" (또는 원하는 이름)
   - "CREATE" 클릭

### Step 4: 자격 증명 다운로드
1. 생성된 OAuth 클라이언트 ID 창에서 **"DOWNLOAD JSON"** 클릭
2. 다운로드된 파일 이름은 `client_secret_XXXXX.json` 형태
3. 이 파일을 프로젝트 루트로 복사하고 이름을 `youtube_credentials.json`으로 변경

### Step 5: Redirect URI 추가 (이메일 로그인용)
1. OAuth 클라이언트 ID 편집 화면으로 이동
2. "Authorized redirect URIs" 섹션에서 "ADD URI" 클릭
3. 다음 URI 추가: `http://localhost:5000/api/youtube/auth/callback`
4. "SAVE" 클릭

## 📁 파일 구조 예시

다운로드한 파일은 다음과 같은 형태입니다:

```json
{
  "installed": {
    "client_id": "123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com",
    "project_id": "your-project-name-123456",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "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45",
    "redirect_uris": ["http://localhost"]
  }
}
```

## ✅ 확인 방법

파일이 올바르게 생성되었는지 확인:

```bash
cd /Users/changikchoi/Documents/study_english_with_sutis
ls -la youtube_credentials.json
cat youtube_credentials.json | grep client_id
```

## 🚀 다음 단계

1. `youtube_credentials.json` 파일을 프로젝트 루트에 배치
2. Redirect URI 설정 (Step 5)
3. 애플리케이션 재시작
4. 이메일 입력 후 로그인 테스트

## 📚 더 자세한 설명

- [YouTube Setup Guide (English)](docs/YOUTUBE_SETUP_GUIDE_eng.md)
- [YouTube Setup Guide (Korean)](docs/YOUTUBE_SETUP_GUIDE_kor.md)

