# LangFlix API 참조

## 개요

LangFlix API는 비디오 처리, 작업 관리, 결과 검색을 위한 RESTful 엔드포인트를 제공합니다. API는 FastAPI로 구축되었으며 자동 OpenAPI 문서를 제공합니다.

## 기본 URL

```
http://localhost:8000
```

## 인증

현재 API는 인증이 필요하지 않습니다. 인증은 Phase 2에서 추가될 예정입니다.

## API 엔드포인트

### 상태 확인

#### GET /health

API 서비스의 상태를 확인합니다.

**응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T10:00:00Z",
  "service": "LangFlix API",
  "version": "1.0.0"
}
```

#### GET /health/detailed

컴포넌트 상태를 포함한 상세한 상태 정보를 가져옵니다.

**응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T10:00:00Z",
  "components": {
    "database": "healthy",
    "storage": "healthy",
    "llm": "healthy"
  }
}
```

### 작업 관리

#### POST /api/v1/jobs

새로운 비디오 처리 작업을 생성합니다.

**요청:**
- Content-Type: `multipart/form-data`
- 매개변수:
  - `video_file`: 비디오 파일 (MP4, MKV, AVI)
  - `subtitle_file`: 자막 파일 (SRT, VTT)
  - `language_code`: 언어 코드 (예: "en", "ko")
  - `show_name`: TV 프로그램 이름
  - `episode_name`: 에피소드 이름
  - `max_expressions`: 최대 표현식 수 (기본값: 10)
  - `language_level`: 숙련도 수준 (beginner, intermediate, advanced, mixed)
  - `test_mode`: 테스트 모드 활성화 (기본값: false)
  - `no_shorts`: 숏 비디오 생성 건너뛰기 (기본값: false)

**응답:**
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "progress": 0,
  "created_at": "2025-10-21T10:00:00Z"
}
```

#### GET /api/v1/jobs/{job_id}

처리 작업의 상태를 가져옵니다.

**응답:**
```json
{
  "job_id": "uuid",
  "status": "PROCESSING",
  "progress": 75,
  "created_at": "2025-10-21T10:00:00Z",
  "started_at": "2025-10-21T10:01:00Z",
  "completed_at": null,
  "error_message": null
}
```

**상태 값:**
- `PENDING`: 작업 생성됨, 시작되지 않음
- `PROCESSING`: 현재 처리 중
- `COMPLETED`: 성공적으로 완료됨
- `FAILED`: 오류 발생

#### GET /api/v1/jobs/{job_id}/expressions

완료된 작업의 표현식을 가져옵니다.

**응답:**
```json
{
  "job_id": "uuid",
  "expressions": [
    {
      "id": "uuid",
      "expression": "get the ball rolling",
      "translation": "일을 시작하다",
      "dialogue": "Let's get the ball rolling on this project",
      "dialogue_translation": "이 프로젝트를 시작해보자",
      "similar_expressions": ["start working", "begin"],
      "context_start_time": "00:01:23,456",
      "context_end_time": "00:01:25,789",
      "scene_type": "dialogue"
    }
  ],
  "total": 1
}
```

#### GET /api/v1/jobs

선택적 필터링으로 작업 목록을 가져옵니다.

**쿼리 매개변수:**
- `status`: 작업 상태로 필터링
- `limit`: 최대 작업 수 (기본값: 50)
- `offset`: 건너뛸 작업 수 (기본값: 0)

**응답:**
```json
[
  {
    "job_id": "uuid",
    "status": "COMPLETED",
    "progress": 100,
    "created_at": "2025-10-21T10:00:00Z",
    "started_at": "2025-10-21T10:01:00Z",
    "completed_at": "2025-10-21T10:05:00Z",
    "error_message": null
  }
]
```

### 파일 관리

#### GET /api/v1/files/{file_id}

ID로 파일을 다운로드합니다.

**응답:**
- 파일 내용 (바이너리)

#### GET /api/v1/files

선택적 필터링으로 파일 목록을 가져옵니다.

**쿼리 매개변수:**
- `job_id`: 작업 ID로 필터링
- `file_type`: 파일 유형으로 필터링

**응답:**
```json
{
  "files": [
    {
      "file_id": "uuid",
      "job_id": "uuid",
      "file_type": "video",
      "filename": "context_video.mkv",
      "size": 1024000,
      "created_at": "2025-10-21T10:00:00Z"
    }
  ]
}
```

#### DELETE /api/v1/files/{file_id}

ID로 파일을 삭제합니다.

**응답:**
```json
{
  "message": "File deleted successfully"
}
```

## 오류 처리

API는 표준 HTTP 상태 코드를 사용하며 일관된 형식으로 오류 정보를 반환합니다.

### 오류 응답 형식

```json
{
  "error": "ErrorType",
  "message": "사람이 읽을 수 있는 오류 메시지",
  "details": {
    "additional": "오류 세부사항"
  }
}
```

### 일반적인 오류 코드

- `400 Bad Request`: 잘못된 요청 매개변수
- `404 Not Found`: 리소스를 찾을 수 없음
- `422 Unprocessable Entity`: 처리 오류
- `500 Internal Server Error`: 서버 오류

## API 문서

대화형 API 문서는 다음에서 사용할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 예제

### 작업 생성

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitles.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01"
```

### 작업 상태 확인

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}"
```

### 작업 결과 가져오기

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}/expressions"
```

## 속도 제한

현재 속도 제한이 없습니다. 속도 제한은 Phase 2에서 구현될 예정입니다.

## 버전 관리

API는 URL 버전 관리를 사용합니다. 현재 버전은 v1입니다.

## 지원

API 지원 및 질문은 메인 문서를 참조하거나 저장소에 이슈를 생성해 주세요.
