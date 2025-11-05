# Redirect URI Mismatch 에러 해결 방법

## 🔴 에러: "Error 400: redirect_uri_mismatch"

이 에러는 Google Cloud Console에 등록된 Redirect URI와 코드에서 사용하는 URI가 일치하지 않을 때 발생합니다.

## ✅ 해결 방법

### 1. Google Cloud Console에서 Redirect URI 추가

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 선택: **gen-lang-client-0804178165**
3. "APIs & Services" → "Credentials" 이동
4. OAuth 2.0 Client ID 클릭 (560775166705-...로 시작하는 것)
5. "Authorized redirect URIs" 섹션 찾기
6. "ADD URI" 버튼 클릭
7. 다음 URI 입력:
   ```
   http://localhost:5000/api/youtube/auth/callback
   ```
8. (선택) 추가 URI:
   ```
   http://127.0.0.1:5000/api/youtube/auth/callback
   ```
9. "SAVE" 버튼 클릭

### 2. 확인 사항

코드에서 사용하는 Redirect URI:
- `http://localhost:5000/api/youtube/auth/callback`

현재 `youtube_credentials.json` 파일에는 이미 추가되어 있습니다:
```json
"redirect_uris": [
  ...
  "http://localhost:5000/api/youtube/auth/callback"
]
```

**하지만 Google Cloud Console에도 반드시 추가해야 합니다!**

### 3. 변경사항 적용 대기

Google Cloud Console에서 URI를 추가한 후:
- 즉시 적용될 수 있지만, 때때로 1-2분 정도 걸릴 수 있습니다
- 브라우저 캐시를 지우고 다시 시도하세요

### 4. 테스트

1. Google Cloud Console에 Redirect URI 추가 완료
2. 애플리케이션 재시작 (선택사항)
3. 이메일 입력 후 "Login to YouTube" 클릭
4. 팝업에서 Google 로그인 진행

## 🔍 디버깅

만약 여전히 에러가 발생한다면:

1. **정확한 URI 확인:**
   ```bash
   # 코드에서 사용하는 URI 확인
   grep -r "redirect_uri" langflix/youtube/web_ui.py
   ```

2. **Google Cloud Console에서 확인:**
   - OAuth 클라이언트 ID 편집 화면
   - "Authorized redirect URIs" 목록에 다음이 포함되어 있는지 확인:
     - `http://localhost:5000/api/youtube/auth/callback`
   
3. **파일에서 확인:**
   ```bash
   cat youtube_credentials.json | grep -A 5 redirect
   ```

## 📌 중요 사항

- **파일 (`youtube_credentials.json`)**에 URI가 있어도 **Google Cloud Console에도 반드시 추가**해야 합니다
- URI는 정확히 일치해야 합니다 (대소문자, 슬래시 포함)
- 포트 번호가 일치하는지 확인하세요 (5000)

