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

### 5단계: Redirect URI 설정 (이메일 기반 로그인용) ⚠️ 필수!

**중요:** 이메일 기반 로그인을 사용하려면 Google Cloud Console에 Redirect URI를 **반드시** 추가해야 합니다. 이 단계를 건너뛰면 "Error 400: redirect_uri_mismatch" 에러가 발생합니다.

1. Google Cloud Console로 돌아가기 → "API 및 서비스" → "사용자 인증 정보"
2. OAuth 2.0 클라이언트 ID 클릭
3. "승인된 리디렉션 URI"에서 "URI 추가" 클릭
4. 추가: `http://localhost:5000/api/youtube/auth/callback`
5. (선택) 추가: `http://127.0.0.1:5000/api/youtube/auth/callback`
6. "저장" 클릭

**중요:** "데스크톱 앱" 자격 증명을 다운로드했더라도, Web Flow 지원을 위해 이 Redirect URI를 추가할 수 있습니다. 자격 증명 파일의 Redirect URI는 자동으로 업데이트되지만, **Google Cloud Console에도 수동으로 추가해야 합니다**.

**참고:** Google Cloud Console에 URI를 추가한 후 변경사항이 반영되기까지 1-2분 정도 걸릴 수 있습니다.

### 6단계: 인증 테스트

LangFlix는 두 가지 인증 방법을 지원합니다:

**옵션 1: 이메일 기반 로그인 (권장)**
- **필요 사항:** 5단계에서 Redirect URI 설정 완료
- **단계:**
  1. 애플리케이션 시작
  2. 입력 필드에 Google 이메일 주소 입력 (선택사항이지만 권장)
  3. "Login to YouTube" 클릭
  4. 팝업 창이 열리고 Google 계정으로 로그인 요청
  5. 승인 후 팝업이 자동으로 닫히고 인증 완료
- **장점:**
  - 사용할 Google 계정 선택 가능
  - 웹 기반 사용자 경험 향상
  - 브라우저 자동 열림 없음

**옵션 2: 기본 브라우저 로그인 (Desktop Flow)**
- **필요 사항:** `youtube_credentials.json` 파일만 필요
- **단계:**
  1. 애플리케이션 시작
  2. 이메일 필드를 비워둠
  3. "Login to YouTube" 클릭
  4. 기본 브라우저가 자동으로 열려 인증 진행
- **장점:**
  - Redirect URI 설정 불필요
  - 기본 사용을 위한 간단한 설정

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

### 오류: "Redirect URI mismatch" 또는 "Error 400: redirect_uri_mismatch"

이 에러는 애플리케이션이 사용하는 Redirect URI가 Google Cloud Console에 설정된 것과 일치하지 않을 때 발생합니다.

**해결 방법:**
1. Google Cloud Console에서 "API 및 서비스" → "사용자 인증 정보"로 이동
2. OAuth 2.0 클라이언트 ID 클릭
3. "승인된 리디렉션 URI"에 추가:
   - `http://localhost:5000/api/youtube/auth/callback` (이메일 로그인 필수)
   - `http://127.0.0.1:5000/api/youtube/auth/callback` (선택)
4. "저장" 클릭
5. 변경사항 반영을 위해 1-2분 대기
6. 다시 로그인 시도

**참고:** `youtube_credentials.json` 파일의 Redirect URI는 애플리케이션이 자동으로 업데이트하지만, **Google Cloud Console에도 수동으로 추가해야 합니다**.

더 자세한 문제 해결 방법은 [REDIRECT_URI_FIX_kor.md](./youtube/REDIRECT_URI_FIX_kor.md)를 참고하세요.

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

