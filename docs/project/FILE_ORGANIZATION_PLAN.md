# 파일 정리 계획 (File Organization Plan)

## 파일 상태 분석

### 1. SHORT_FORM_REFACTORING_PLAN.md
**상태:** ✅ 완료됨 (아카이브 이동 필요)
- **확인 결과**: 리팩토링이 이미 완료됨 (TICKET-001)
- CHANGELOG.md에 "Short-form logic simplified (~180 lines removed)" 기록됨
- 코드에서 불필요한 audio extraction 코드가 제거됨
- 현재 구현은 계획서의 Target State와 일치함

**권장 조치:**
- `docs/archive/` 폴더로 이동
- 파일명: `SHORT_FORM_REFACTORING_PLAN.md` (유지)
- 참고용으로 보관 (역사 기록)

---

### 2. SETUP_GUIDE.md
**상태:** ✅ 필요함 (위치 검토 필요)
- **용도**: 사용자 설정 가이드
- **현재 위치**: 루트 디렉토리
- **내용**: 프로젝트 설정, 설치, 실행 방법

**권장 조치:**
- **옵션 1**: 루트에 유지 (일반적인 프로젝트 구조)
- **옵션 2**: `docs/` 폴더로 이동 (다른 가이드와 함께)
- **추천**: 루트에 유지하되, `docs/README.md`에서 링크 추가

---

### 3. REDIRECT_URI_FIX.md
**상태:** ✅ 필요함 (위치 이동 필요)
- **용도**: YouTube OAuth 리다이렉트 URI 문제 해결 가이드
- **현재 위치**: 루트 디렉토리
- **관련 문서**: `docs/youtube/` 폴더에 YouTube 관련 문서 존재

**권장 조치:**
- `docs/youtube/` 폴더로 이동
- 파일명: `REDIRECT_URI_FIX_eng.md` (영문), `REDIRECT_URI_FIX_kor.md` (한글)
- 또는 `docs/TROUBLESHOOTING_GUIDE.md`에 통합

---

### 4. CHANGELOG.md
**상태:** ✅ 필요함 (위치 적절)
- **용도**: 프로젝트 변경 로그 (Keep a Changelog 표준)
- **현재 위치**: 루트 디렉토리 ✅ (표준 위치)
- **내용**: 최신 버전까지 업데이트됨

**권장 조치:**
- **위치 유지** (루트 디렉토리가 표준)
- README.md에서 링크 확인

---

## 권장 파일 구조

```
project-root/
├── CHANGELOG.md                    ✅ 유지 (표준 위치)
├── SETUP_GUIDE.md                  ✅ 유지 또는 docs/로 이동
├── README.md                       ✅ 유지 (메인 문서)
├── REDIRECT_URI_FIX.md             ❌ docs/youtube/로 이동
├── SHORT_FORM_REFACTORING_PLAN.md  ❌ docs/archive/로 이동
│
├── docs/
│   ├── README.md                   (SETUP_GUIDE.md 링크 추가)
│   ├── TROUBLESHOOTING_GUIDE.md   (REDIRECT_URI_FIX 내용 통합 고려)
│   ├── youtube/
│   │   ├── README_eng.md
│   │   ├── README_kor.md
│   │   └── REDIRECT_URI_FIX_eng.md    ← 이동
│   │   └── REDIRECT_URI_FIX_kor.md    ← 이동 (한글 버전 생성)
│   └── archive/
│       └── SHORT_FORM_REFACTORING_PLAN.md  ← 이동
```

---

## 실행 계획

### Step 1: 아카이브 이동 (완료된 계획서)
```bash
mv SHORT_FORM_REFACTORING_PLAN.md docs/archive/
```

### Step 2: 문제 해결 가이드 이동
```bash
# YouTube 관련 문서 폴더로 이동
mv REDIRECT_URI_FIX.md docs/youtube/REDIRECT_URI_FIX_eng.md

# 한글 버전 생성 (선택사항)
# 또는 TROUBLESHOOTING_GUIDE.md에 통합
```

### Step 3: 문서 업데이트
- `docs/README.md`에 SETUP_GUIDE.md 링크 추가
- `docs/youtube/README_eng.md`에 REDIRECT_URI_FIX 링크 추가
- `docs/TROUBLESHOOTING_GUIDE.md`에 YouTube OAuth 섹션 추가 (선택)

---

## 파일별 상세 분석

### SHORT_FORM_REFACTORING_PLAN.md
**완료 여부 확인:**
- ✅ Step 1: 불필요한 audio extraction 제거됨 (코드 확인)
- ✅ Step 2: Expression processing이 slide 생성 전으로 이동됨
- ✅ Step 3: Slide creation이 concat 후로 이동됨
- ✅ Step 4: vstack 사용 패턴 단순화됨
- ✅ Step 5: Final gain 적용 유지됨

**결론:** 리팩토링 완료, 아카이브로 이동 권장

### SETUP_GUIDE.md
**내용 확인:**
- ✅ 프로젝트 개요
- ✅ 설치 방법 (Docker, 로컬)
- ✅ 환경 변수 설정
- ✅ 테스트 실행
- ✅ 문제 해결 가이드 링크

**결론:** 필요함, 루트 또는 docs/ 유지

### REDIRECT_URI_FIX.md
**내용 확인:**
- ✅ 특정 문제 해결 가이드 (YouTube OAuth)
- ✅ Google Cloud Console 설정 방법
- ✅ 디버깅 팁

**결론:** 필요함, docs/youtube/로 이동 권장

### CHANGELOG.md
**내용 확인:**
- ✅ 최신 버전까지 업데이트됨
- ✅ TICKET-001 완료 기록 포함
- ✅ 표준 Keep a Changelog 형식

**결론:** 필요함, 위치 적절 (루트 유지)

---

## 최종 권장사항

1. **SHORT_FORM_REFACTORING_PLAN.md** → `docs/archive/` 이동 (완료된 작업)
2. **REDIRECT_URI_FIX.md** → `docs/youtube/REDIRECT_URI_FIX_eng.md` 이동
3. **SETUP_GUIDE.md** → 루트 유지 (또는 docs/로 이동 후 README.md 링크)
4. **CHANGELOG.md** → 루트 유지 (표준 위치)

