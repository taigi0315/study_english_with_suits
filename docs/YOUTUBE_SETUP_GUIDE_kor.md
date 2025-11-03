# YouTube API 설정 가이드

## 개요

LangFlix에서 YouTube 업로드 기능을 사용하려면 Google Cloud Console에서 OAuth 2.0 자격 증명을 설정해야 합니다. 이는 LLM 기능에 사용하는 **Gemini API 키와는 별개**입니다.

## 단계별 설정 방법

### 1단계: Google Cloud 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트를 생성하거나 기존 프로젝트 선택
3. **YouTube Data API v3** 활성화:
   - "API 및 서비스" → "라이브러리"로 이동
   - "YouTube Data API v3" 검색
   - "사용 설정" 클릭

### 2단계: OAuth 2.0 자격 증명 생성

1. "API 및 서비스" → "사용자 인증 정보"로 이동
2. "사용자 인증 정보 만들기" → "OAuth 클라이언트 ID" 클릭
3. 필요시 OAuth 동의 화면 구성:
   - "외부" (개인용) 또는 "내부" (Google Workspace용) 선택
   - 필수 필드 입력 (앱 이름, 사용자 지원 이메일 등)
   - 외부 타입 사용 시 테스트 사용자에 이메일 추가
   - 단계를 진행하며 저장
4. 애플리케이션 유형에서 **"데스크톱 앱"** 선택
5. 이름 지정 (예: "LangFlix YouTube Uploader")
6. "만들기" 클릭
7. **자격 증명 JSON 파일 다운로드**

### 3단계: 자격 증명 파일 저장

1. 다운로드된 파일 이름은 `client_secret_XXXXX.json` 형태입니다
2. 파일 이름을 `youtube_credentials.json`으로 변경
3. **프로젝트 루트 디렉토리**에 저장 (`config.yaml`과 같은 위치)

**파일 위치 예시:**
```
study_english_with_sutis/
├── config.yaml
├── youtube_credentials.json  ← 여기에 저장
├── langflix/
└── ...
```

### 4단계: 파일 위치 확인

자격 증명 파일 위치:
```bash
/Users/changikchoi/Documents/study_english_with_sutis/youtube_credentials.json
```

존재 여부 확인:
```bash
ls -la youtube_credentials.json
```

### 5단계: 인증 테스트

1. 애플리케이션 시작
2. UI의 YouTube 섹션에서 "Login" 클릭
3. 브라우저 창이 열리고 Google 계정으로 로그인 요청
4. 승인 후 리디렉션되어 인증 완료

## 파일 구조

자격 증명 파일 (`youtube_credentials.json`)은 다음과 같은 형태입니다:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

## 중요 사항

### Gemini API 키와의 차이점

- **Gemini API 키** (`.env`에 저장): LLM 텍스트 생성에 사용
- **YouTube OAuth 자격 증명** (`youtube_credentials.json`): YouTube API 인증에 사용
- 두 기능을 모두 사용하려면 **둘 다 필요**하며 서로 별개입니다

### 보안

- `youtube_credentials.json`에는 민감한 정보가 포함됩니다
- **절대 git에 커밋하지 마세요** (`.gitignore`에 포함되어야 함)
- 안전하게 보관하고 공개하지 마세요

### 첫 인증 시

- 처음 로그인 시 브라우저 창이 열립니다
- Google 계정으로 로그인 요청
- 승인 후 토큰 파일 (`youtube_token.json`)이 자동 생성됩니다
- 이후 로그인은 토큰 파일을 사용합니다 (브라우저 프롬프트 없음)

## 문제 해결

### 오류: "Credentials file not found"

**해결 방법:**
1. 파일 존재 확인: `ls -la youtube_credentials.json`
2. 프로젝트 루트 디렉토리에 있는지 확인
3. 파일 이름이 정확히 `youtube_credentials.json`인지 확인 (대소문자 구분)

### 오류: "Port 8080 is already in use"

**해결 방법:**
1. 포트 8080을 사용하는 다른 애플리케이션 종료
2. 또는 코드를 수정하여 다른 포트 사용 (코드 변경 필요)

### 오류: "Access blocked: This app's request is invalid"

**해결 방법:**
1. OAuth 동의 화면이 올바르게 구성되었는지 확인
2. 외부 타입 사용 시 이메일을 "테스트 사용자"에 추가
3. OAuth 클라이언트 ID 유형이 "데스크톱 앱"인지 확인

### 오류: "Redirect URI mismatch"

**해결 방법:**
1. Google Cloud Console에서 OAuth 2.0 클라이언트로 이동
2. 승인된 리디렉션 URI에 `http://localhost:8080/` 추가
3. 다른 포트 사용 시 해당 포트 추가

## 다음 단계

자격 증명 설정 후:

1. ✅ `youtube_credentials.json`을 프로젝트 루트에 배치
2. ✅ UI에서 "Login" 클릭
3. ✅ 브라우저 창에서 승인
4. ✅ 비디오 업로드 스케줄링 시작!

## 관련 문서

- [YouTube Integration Guide](./archive/en/YOUTUBE_INTEGRATION.md) - 전체 API 참조
- [Configuration Guide](./CONFIGURATION_GUIDE.md) - 일반 설정
- [Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md) - 일반적인 문제 및 해결 방법

