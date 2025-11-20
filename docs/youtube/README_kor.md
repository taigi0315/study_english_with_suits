# YouTube 모듈 문서 (KOR)

**최종 업데이트:** 2025-01-30

## 개요

`langflix/youtube/` 모듈은 교육용 비디오의 관리, 업로드, 스케줄링을 위한 YouTube 자동화 기능을 제공합니다. 비디오 파일 관리, 메타데이터 생성, OAuth 인증을 통한 업로드 처리, 할당량 관리가 포함된 스케줄링, 그리고 비디오 관리를 위한 웹 기반 UI를 포함합니다.

## 폴더 구조

- `video_manager.py`: 비디오 파일 스캔, 메타데이터 추출, 파일 관리
- `uploader.py`: YouTube API 인증 및 비디오 업로드 기능
- `metadata_generator.py`: YouTube 메타데이터(제목, 설명, 태그) 생성
- `schedule_manager.py`: 일일 제한 및 할당량 관리가 포함된 업로드 스케줄링
- `web_ui.py`: 비디오 관리 대시보드를 위한 Flask 기반 웹 인터페이스

## 주요 구성 요소

### VideoFileManager (`video_manager.py`)

생성된 비디오 파일을 YouTube 업로드를 위해 관리합니다.

**주요 기능:**
- 출력 디렉토리에서 비디오 파일 스캔
- ffprobe를 사용한 메타데이터 추출(길이, 해상도, 형식)
- 비디오 경로를 파싱하여 타입, 에피소드, 표현식 결정
- Redis와 통합하여 비디오 메타데이터 캐싱
- 데이터베이스에서 업로드 상태 확인
- 타입, 에피소드, 업로드 준비 상태별 비디오 필터링

**주요 메서드:**
- `scan_all_videos(force_refresh=False)`: 모든 비디오 파일 스캔 및 메타데이터 추출
- `get_uploadable_videos(videos)`: 업로드 준비된 비디오 필터링(최종 및 숏 타입)
- `get_videos_by_type(videos, video_type)`: 타입별 필터링
- `get_videos_by_episode(videos, episode)`: 에피소드별 필터링
- `get_upload_ready_videos(videos)`: 업로드 준비된 비디오 가져오기
- `get_statistics(videos)`: 비디오 통계 가져오기

**캐싱:**
- Redis를 사용한 비디오 메타데이터 캐싱(5분 TTL)
- 비디오 처리 완료 시 캐시 무효화
- 캐시 사용 불가 시 파일시스템 스캔으로 폴백

### YouTubeUploader (`uploader.py`)

YouTube API 인증 및 비디오 업로드를 처리합니다.

**주요 기능:**
- Google OAuth 2.0 인증
- 토큰 관리 및 갱신
- 진행 상황 추적이 포함된 비디오 업로드
- 메타데이터 업로드(제목, 설명, 태그, 공개 설정, 카테고리)
- 예약 발행 지원
- 오류 처리 및 재시도 로직

**OAuth 상태 저장소:**
- Redis를 사용한 OAuth 상태 저장 지원(웹 기반 인증 흐름용)
- Redis 사용 불가 시 메모리 저장소로 폴백
- OAuth 흐름에서 CSRF 공격 방지

### YouTubeMetadataGenerator (`metadata_generator.py`)

교육용 비디오의 YouTube 메타데이터를 생성합니다.

**주요 기능:**
- 템플릿 기반 메타데이터 생성
- 다양한 비디오 타입 지원(교육용, 숏, 최종)
- 동적 콘텐츠 대체(표현식, 번역, 에피소드)
- SEO 최적화된 제목 및 설명
- YouTube 카테고리 매핑

**템플릿:**
- 교육용, 숏, 최종 비디오 타입에 대한 사전 구성된 템플릿
- 설정을 통한 사용자 정의 템플릿
- 다국어 지원

### YouTubeScheduleManager (`schedule_manager.py`)

일일 제한 및 할당량 관리가 포함된 YouTube 업로드 스케줄링을 관리합니다.

**주요 기능:**
- 일일 업로드 제한(설정 가능: 기본값 일일 최종 2개, 숏 5개)
- 선호 발행 시간(예: 10:00, 14:00, 18:00)
- 할당량 추적 및 관리
- 할당량 경고 임계값(기본값 80%)
- SQLAlchemy를 사용한 데이터베이스 기반 스케줄링
- 데이터베이스 레벨 잠금을 통한 경쟁 조건 방지

**데이터베이스 통합:**
- 데이터베이스 세션을 위해 `db_manager.session()` 컨텍스트 매니저 사용
- `YouTubeSchedule` 테이블에 스케줄 저장
- `YouTubeQuotaUsage` 테이블에서 할당량 사용량 추적
- 데이터베이스 레벨 잠금으로 경쟁 조건 방지(TICKET-021)

**최근 수정사항 (TICKET-021):**
- 동시 스케줄링 요청의 경쟁 조건 수정
- 스케줄 생성 시 데이터베이스 레벨 잠금 추가
- 데이터베이스 연결 오류 처리 개선
- 할당량 경고 임계값 계산 수정(비율에서 퍼센트로 변경)

### VideoManagementUI (`web_ui.py`)

비디오 관리 대시보드를 위한 Flask 기반 웹 인터페이스입니다.

**주요 기능:**
- **파일 탐색기 인터페이스**: 디렉토리 기반 탐색 (output/ → Series/ → Episode/ → shorts/ 또는 long/)
- 비디오 목록 및 필터링
- 진행 상황 추적이 포함된 업로드 관리
- 스케줄 관리 인터페이스
- 통계 대시보드
- YouTube OAuth 인증 흐름
- 일괄 작업(다중 선택 업로드)
- 실시간 작업 상태 업데이트
- 디렉토리 탐색을 위한 Breadcrumb 네비게이션

**주요 라우트:**
- `/`: 파일 탐색기가 포함된 메인 대시보드(HTML)
- `/api/videos`: 모든 비디오 가져오기(JSON)
- `/api/videos/<video_type>`: 타입별 비디오 가져오기
- `/api/videos/episode/<episode>`: 에피소드별 비디오 가져오기
- `/api/upload-ready`: 업로드 준비된 비디오 가져오기
- `/api/statistics`: 비디오 통계 가져오기
- `/api/explore`: 디렉토리 구조 탐색 (신규)
- `/api/explore/file-info`: 상세 파일 정보 가져오기 (신규)
- `/api/upload`: YouTube에 비디오 업로드
- `/api/schedule`: 비디오 업로드 스케줄링
- `/api/schedule/<schedule_id>`: 스케줄 가져오기/업데이트/삭제
- `/api/oauth/authorize`: OAuth 흐름 시작
- `/api/oauth/callback`: OAuth 콜백 처리
- `/api/thumbnail/<video_path>`: 비디오 썸네일 생성 및 제공 (임시 파일 사용)

**UI 기능:**
- **파일 탐색기 뷰**: 파일 관리자처럼 output 디렉토리 구조 탐색
- **리스트 뷰**: 메타데이터가 포함된 비디오 파일의 간결한 리스트 표시
- **Breadcrumb 네비게이션**: 디렉토리 레벨 간 쉬운 탐색
- **필터링**: 비디오 타입(short-form, long-form), 업로드 상태별 필터링
- **검색**: 파일명으로 파일 검색
- **일괄 선택**: 일괄 업로드 작업을 위한 여러 비디오 선택
- **파일 필터링**: 시스템 파일(.DS_Store) 및 썸네일 파일 자동 필터링

**최근 개선사항 (2025-01):**
- 평면 비디오 리스트를 파일 탐색기 인터페이스로 교체
- 더 나은 조직화를 위한 디렉토리 기반 탐색
- 시스템 파일(.DS_Store) 자동 필터링
- 임시 파일을 사용한 썸네일 생성(디스크 저장 없음)
- 전체 파일명 표시가 포함된 개선된 리스트 뷰
- 더 깔끔한 UI를 위해 중복 메타데이터 제거(에피소드 이름, 파일 크기)

**최근 개선사항 (TICKET-021):**
- 일괄 비디오 관리를 위한 다중 선택 체크박스
- 오류 처리 및 사용자 피드백 개선
- 스케줄 관리 UI/UX 개선
- 실시간 할당량 상태 표시

## 사용 예제

### 스케줄링과 함께 비디오 업로드

```python
from langflix.youtube.uploader import YouTubeUploadManager
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.schedule_manager import YouTubeScheduleManager

# 컴포넌트 초기화
upload_manager = YouTubeUploadManager()
metadata_generator = YouTubeMetadataGenerator()
schedule_manager = YouTubeScheduleManager()

# 메타데이터 생성
metadata = metadata_generator.generate_metadata(
    video_type="educational",
    expression="Break the ice",
    translation="분위기를 깨다",
    episode="S01E01",
    language="ko"
)

# 다음 사용 가능한 슬롯 가져오기
scheduled_time = schedule_manager.get_next_available_slot(
    video_type="final",
    preferred_date=date.today()
)

# 스케줄링과 함께 업로드
result = upload_manager.upload_video(
    video_path="output/educational_Break_the_ice.mkv",
    metadata=metadata,
    scheduled_time=scheduled_time
)
```

### 비디오 스캔 및 필터링

```python
from langflix.youtube.video_manager import VideoFileManager

# 매니저 초기화
manager = VideoFileManager(output_dir="output")

# 모든 비디오 스캔
all_videos = manager.scan_all_videos()

# 타입별 필터링
final_videos = manager.get_videos_by_type(all_videos, "final")
short_videos = manager.get_videos_by_type(all_videos, "short")

# 업로드 준비된 비디오 가져오기
ready_videos = manager.get_upload_ready_videos(all_videos)
```

### 할당량 상태 확인

```python
from langflix.youtube.schedule_manager import YouTubeScheduleManager
from datetime import date

schedule_manager = YouTubeScheduleManager()

# 오늘의 할당량 확인
quota_status = schedule_manager.check_daily_quota(date.today())

print(f"최종 비디오: {quota_status.final_used}/{quota_status.final_remaining + quota_status.final_used}")
print(f"숏 비디오: {quota_status.short_used}/{quota_status.short_remaining + quota_status.short_used}")
print(f"할당량: {quota_status.quota_percentage:.1f}%")
```

## 의존성

- **google-api-python-client**: YouTube API 클라이언트
- **google-auth-httplib2**: Google Auth용 HTTP 전송
- **google-auth-oauthlib**: Google용 OAuth 2.0 흐름
- **flask**: UI용 웹 프레임워크
- **sqlalchemy**: 스케줄링용 데이터베이스 ORM
- **ffprobe**: 비디오 메타데이터 추출(외부 바이너리)

## 설정

### OAuth 자격 증명

1. Google Cloud Console에서 OAuth 2.0 자격 증명 생성
2. 자격 증명을 `youtube_credentials.json`으로 다운로드
3. 프로젝트 루트에 배치하거나 경로 구성

### 스케줄 설정

`ScheduleConfig`에서 구성:
- `daily_limits`: 비디오 타입별 일일 업로드 제한
- `preferred_times`: 선호 발행 시간(HH:MM 형식)
- `quota_limit`: 일일 할당량 제한(기본값: 10000)
- `warning_threshold`: 경고 임계값 퍼센트(기본값: 80%)

## 오류 처리

모든 컴포넌트에 포괄적인 오류 처리가 포함됩니다:
- 데이터베이스 연결 오류는 우아하게 처리됩니다
- OAuth 토큰 갱신은 자동입니다
- 업로드 실패는 로깅되고 보고됩니다
- 스케줄 충돌은 데이터베이스 잠금으로 방지됩니다

## 관련 문서

- [데이터베이스 모듈 문서](../db/README_kor.md) - 데이터베이스 스키마 및 모델
- [서비스 모듈 문서](../services/README_kor.md) - 작업 큐 및 파이프라인 서비스
- [API 모듈 문서](../api/README_kor.md) - FastAPI 엔드포인트
- [스토리지 모듈 문서](../storage/README_kor.md) - 스토리지 백엔드 통합

## 테스트

테스트는 `tests/youtube/`에 위치합니다:
- `test_video_manager.py`: 비디오 파일 관리 테스트
- `test_uploader.py`: 업로드 기능 테스트
- `test_metadata_generator.py`: 메타데이터 생성 테스트
- `test_schedule_manager.py`: 스케줄링 테스트

## 최근 변경사항

### TICKET-021: 스케줄러 경쟁 조건 수정
- 스케줄 생성 시 데이터베이스 레벨 잠금 추가
- 동시 스케줄링 요청의 경쟁 조건 수정
- 할당량 경고 임계값 계산 개선(비율 대신 퍼센트)
- 데이터베이스 연결 오류 처리 향상

### TICKET-020: 예약된 시간 불일치 수정
- UI와 백엔드에서 시간대 처리 수정
- 컴포넌트 간 일관된 시간 표현 보장

### TICKET-019: 숏폼 비디오 길이 제한
- 숏폼 비디오 길이 제한 감소
- 검증 및 오류 메시지 개선

### TICKET-018: 예약된 YouTube 업로드 프로세서
- 예약된 업로드를 위한 백그라운드 프로세서 구현
- 예약된 시간에 자동 업로드 실행 추가
- 작업 추적 및 상태 업데이트 개선

