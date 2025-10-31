## 🎯 이제 사용 방법:

### 1️⃣ **문서화 작업** (처음 시작)
```
Cursor Composer (Cmd+I)에서:

@docs 폴더를 열고
langflix/ 폴더의 코드를 깊이 리뷰해서
docs/ 에 문서를 생성해줘

각 폴더별로 README.md를 만들고
마지막에 docs/project.md로 전체 요약해줘
```

### 2️⃣ **코드 리뷰 & 티켓 생성**
```
@langflix 폴더의 코드를 시니어 엔지니어 관점에서 리뷰해줘

주요 워크플로우를 추적하면서:
- 중복 코드
- 테스트 커버리지
- 성능 이슈
- 리팩토링 기회

tickets/review-required/ 에 티켓을 생성해줘
```

### 3️⃣ **아키텍트 리뷰**
```
먼저 @docs/ 모든 다큐먼트를 읽고 시스템을 이해한 다음

@tickets/review-required/ 의 모든 티켓을 리뷰해서:
- 승인할 것은 tickets/approved/ 로
- 거절할 것은 tickets/rejected/ 로
- 보류할 것은 tickets/deferred/ 로

그리고 tickets/approved/IMPLEMENTATION-ROADMAP.md 를 생성해줘
```

### 4️⃣ **구현 작업**
```
@tickets/approved/IMPLEMENTATION-ROADMAP.md 를 확인하고

TICKET-001을 구현해줘:
1. feature/TICKET-001-xxx 브랜치 생성
2. 테스트 먼저 작성
3. 코드 구현
4. 문서 업데이트 (한글/영문)
5. tickets/done/ 으로 이동
```

## 💡 추가 팁:

**문제가 생기면:**
- Cursor 재시작
- `.cursorrules` 파일이 프로젝트 **최상위**에 있는지 확인
- 파일 이름이 정확히 `.cursorrules` 인지 확인 (앞에 점 있어야 함)

**테스트 해보기:**
```
Cursor Composer에서:

"현재 설정된 instruction을 요약해줘"

또는

"내가 docs/ 폴더에서 작업하면 어떤 역할을 해야 해?"