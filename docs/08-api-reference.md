# API Reference

## Overview

This document provides reference for the LangFlix REST API endpoints.

## Job Management

### Get Queue Status

Retrieves the current status of the job processing queue, including processor state, queued items, currently processing job, and recent system logs.

**Endpoint:** `GET /api/jobs/queue/status`

**Response:**

```json
{
  "processor": "idle", // or "processing", "waiting"
  "queue": {
    "length": 0,
    "items": [],
    "next_items_count": 0
  },
  "current_job": null,
  "logs": [
    "2024-01-01 12:00:00 | INFO     | api.routes.jobs      | Checking queue status...",
    "..."
  ]
}
```

## See Also

- `SYSTEM_ARCHITECTURE.md` - For high-level architecture involving the API.
