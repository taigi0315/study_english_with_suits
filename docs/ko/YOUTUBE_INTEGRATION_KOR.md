# YouTube 통합 가이드

## 개요

LangFlix YouTube 통합은 지능적인 할당량 관리와 메타데이터 생성을 통한 자동화된 비디오 업로드 스케줄링을 제공합니다. 이 시스템을 통해 일일 제한과 API 할당량을 준수하면서 교육용 비디오(final 및 short 형식)를 YouTube에 업로드할 수 있습니다.

## 주요 기능

### 🎯 핵심 기능
- **계정 관리**: YouTube OAuth 2.0을 통한 로그인/로그아웃
- **스마트 스케줄링**: 자동 다음 가능 시간 계산
- **일일 제한**: 업로드 제한 강제 (final 비디오 2개, shorts 5개/일)
- **할당량 관리**: YouTube API 사용량 추적 및 경고 제공
- **메타데이터 생성**: 제목, 설명, 태그 자동 생성
- **비디오 필터링**: 업로드용 final 및 short 비디오만 표시

### 📅 스케줄링 시스템
- **선호 시간**: 오전 10시, 오후 2시, 오후 6시 (설정 가능)
- **충돌 해결**: 자동으로 다음 가능한 슬롯 찾기
- **수동 오버라이드**: 사용자 정의 날짜/시간 선택
- **캘린더 뷰**: 예정된 업로드 시각화

### 🔧 기술적 기능
- **데이터베이스 지속성**: 스케줄 및 계정 정보 저장
- **오류 처리**: 포괄적인 오류 관리
- **진행 상황 추적**: 실시간 업로드 상태
- **할당량 경고**: 사전 사용량 알림

## API 참조

### 계정 관리

#### GET `/api/youtube/account`
현재 인증된 YouTube 계정 정보를 가져옵니다.

**응답:**
```json
{
  "authenticated": true,
  "channel": {
    "channel_id": "UC...",
    "title": "내 채널",
    "thumbnail_url": "https://...",
    "email": "user@example.com"
  }
}
```

#### POST `/api/youtube/login`
YouTube 인증 (OAuth 플로우 트리거).

**응답:**
```json
{
  "message": "YouTube 인증 성공",
  "channel": { ... }
}
```

#### POST `/api/youtube/logout`
YouTube 로그아웃 (토큰 삭제).

**응답:**
```json
{
  "message": "YouTube 로그아웃 성공"
}
```

### 스케줄 관리

#### GET `/api/schedule/next-available`
비디오 유형에 대한 다음 가능한 업로드 슬롯을 가져옵니다.

**매개변수:**
- `video_type`: "final" 또는 "short"

**응답:**
```json
{
  "next_available_time": "2025-10-25T10:00:00",
  "video_type": "final"
}
```

#### GET `/api/schedule/calendar`
예정된 업로드 캘린더 뷰를 가져옵니다.

**매개변수:**
- `start_date`: ISO 날짜 문자열 (선택사항)
- `days`: 표시할 일수 (기본값: 7)

**응답:**
```json
{
  "2025-10-25": [
    {
      "id": "uuid",
      "video_path": "/path/to/video.mp4",
      "video_type": "final",
      "scheduled_time": "2025-10-25T10:00:00",
      "status": "scheduled"
    }
  ]
}
```

#### POST `/api/upload/schedule`
특정 시간에 비디오 업로드를 스케줄합니다.

**요청 본문:**
```json
{
  "video_path": "/path/to/video.mp4",
  "video_type": "final",
  "publish_time": "2025-10-25T10:00:00" // 선택사항
}
```

**응답:**
```json
{
  "message": "비디오가 2025-10-25T10:00:00에 스케줄됨",
  "scheduled_time": "2025-10-25T10:00:00",
  "video_path": "/path/to/video.mp4",
  "video_type": "final"
}
```

### 할당량 관리

#### GET `/api/quota/status`
YouTube API 할당량 사용 상태를 가져옵니다.

**응답:**
```json
{
  "date": "2025-10-25",
  "final_videos": {
    "used": 1,
    "remaining": 1,
    "limit": 2
  },
  "short_videos": {
    "used": 2,
    "remaining": 3,
    "limit": 5
  },
  "api_quota": {
    "used": 3200,
    "remaining": 6800,
    "percentage": 32.0,
    "limit": 10000
  },
  "warnings": []
}
```

## 사용 예제

### 기본 업로드 스케줄링

```javascript
// 다음 가능한 시간 가져오기
const response = await fetch('/api/schedule/next-available?video_type=final');
const { next_available_time } = await response.json();

// 비디오 스케줄
const scheduleResponse = await fetch('/api/upload/schedule', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_path: '/path/to/video.mp4',
    video_type: 'final',
    publish_time: next_available_time
  })
});
```

### 사용자 정의 시간 스케줄링

```javascript
// 특정 시간에 스케줄
const customTime = new Date('2025-10-25T14:00:00').toISOString();

const response = await fetch('/api/upload/schedule', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_path: '/path/to/video.mp4',
    video_type: 'short',
    publish_time: customTime
  })
});
```

### 계정 관리

```javascript
// YouTube 로그인
const loginResponse = await fetch('/api/youtube/login', {
  method: 'POST'
});

// 계정 상태 확인
const accountResponse = await fetch('/api/youtube/account');
const { authenticated, channel } = await accountResponse.json();

// 로그아웃
const logoutResponse = await fetch('/api/youtube/logout', {
  method: 'POST'
});
```

## 설정

### 환경 변수

```bash
# YouTube API 설정
YOUTUBE_CREDENTIALS_FILE=youtube_credentials.json
YOUTUBE_DAILY_LIMIT_FINAL=2
YOUTUBE_DAILY_LIMIT_SHORT=5
YOUTUBE_QUOTA_LIMIT=10000
YOUTUBE_WARNING_THRESHOLD=0.8
```

### 데이터베이스 설정

시스템은 다음 데이터베이스 테이블을 사용합니다:

- `youtube_schedule`: 예정된 업로드
- `youtube_accounts`: YouTube 계정 정보
- `youtube_quota_usage`: 일일 할당량 추적

### 스케줄링 설정

```python
# 기본 스케줄링 설정
ScheduleConfig(
    daily_limits={'final': 2, 'short': 5},
    preferred_times=['10:00', '14:00', '18:00'],
    quota_limit=10000,
    warning_threshold=0.8
)
```

## 오류 처리

### 일반적인 오류 응답

#### 인증 오류
```json
{
  "error": "인증 실패",
  "code": 401
}
```

#### 할당량 초과
```json
{
  "error": "2025-10-25에 final 비디오 할당량이 없습니다. 사용됨: 2/2",
  "code": 400
}
```

#### 잘못된 비디오 유형
```json
{
  "error": "video_type은 'final' 또는 'short'이어야 합니다",
  "code": 400
}
```

#### 스케줄링 충돌
```json
{
  "error": "요청된 시간 슬롯이 점유됨. 다음 가능: 2025-10-25T14:00:00",
  "code": 400
}
```

## 모범 사례

### 1. 할당량 관리
- 정기적으로 할당량 사용량 모니터링
- 비피크 시간에 업로드 스케줄
- 여러 비디오에 대한 배치 스케줄링 사용

### 2. 스케줄링 전략
- 미리 업로드 계획
- 선호 게시 시간 사용
- 시간대 차이 고려

### 3. 오류 처리
- 실패한 업로드에 대한 재시도 로직 구현
- 할당량 경고 모니터링
- 인증 실패 처리

### 4. 성능
- API 호출에 비동기 작업 사용
- 계정 정보 캐싱
- 데이터베이스 작업 배치

## 문제 해결

### 일반적인 문제

#### 1. 인증 실패
- OAuth 자격 증명 확인
- Google Cloud Console에서 리다이렉트 URI 확인
- 테스트 사용자 권한 확인

#### 2. 할당량 초과
- 일일 제한 설정 확인
- API 사용량 모니터링
- 할당량 경고 구현

#### 3. 스케줄링 충돌
- 자동 스케줄링 사용
- 기존 스케줄 확인
- 시간대 설정 확인

#### 4. 업로드 실패
- 비디오 파일 형식 확인
- 파일 권한 확인
- 네트워크 연결 모니터링

### 디버그 모드

디버그 로깅 활성화:

```python
import logging
logging.getLogger('langflix.youtube').setLevel(logging.DEBUG)
```

## 보안 고려사항

### OAuth 보안
- 토큰을 안전하게 저장
- 토큰 새로고침 구현
- 모든 통신에 HTTPS 사용

### 데이터 보호
- 민감한 데이터 암호화
- 액세스 제어 구현
- 정기적인 보안 감사

### API 보안
- 속도 제한
- 입력 검증
- 오류 메시지 정리

## 모니터링 및 분석

### 주요 지표
- 업로드 성공률
- 할당량 활용률
- 스케줄링 정확도
- 사용자 참여도

### 로깅
- 모든 API 호출 로깅
- 오류 추적
- 성능 지표
- 사용자 작업

## 향후 개선사항

### 계획된 기능
- 대량 업로드 스케줄링
- 고급 분석
- 메타데이터 A/B 테스트
- 다른 플랫폼과의 통합

### 성능 개선
- 캐싱 전략
- 데이터베이스 최적화
- 비동기 처리
- 로드 밸런싱

## 지원

기술 지원이나 기능 요청이 있으시면 프로젝트 문서를 참조하거나 개발팀에 문의하세요.

---

*최종 업데이트: 2025년 10월*
