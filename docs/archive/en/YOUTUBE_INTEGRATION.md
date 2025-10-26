# YouTube Integration Guide

## Overview

The LangFlix YouTube Integration provides automated video upload scheduling with intelligent quota management and metadata generation. This system allows you to schedule educational videos (final and short formats) for YouTube upload while respecting daily limits and API quotas.

## Features

### 🎯 Core Features
- **Account Management**: Login/logout with YouTube OAuth 2.0
- **Smart Scheduling**: Automatic next available time calculation
- **Daily Limits**: Enforce upload limits (2 final videos, 5 shorts per day)
- **Quota Management**: Track YouTube API usage and provide warnings
- **Metadata Generation**: Auto-generate titles, descriptions, and tags
- **Video Filtering**: Only show final and short videos for upload

### 📅 Scheduling System
- **Preferred Times**: 10 AM, 2 PM, 6 PM (configurable)
- **Conflict Resolution**: Automatically find next available slot
- **Manual Override**: Custom date/time selection
- **Calendar View**: Visualize scheduled uploads

### 🔧 Technical Features
- **Database Persistence**: Store schedules and account info
- **Error Handling**: Comprehensive error management
- **Progress Tracking**: Real-time upload status
- **Quota Warnings**: Proactive usage alerts

## API Reference

### Account Management

#### GET `/api/youtube/account`
Get current authenticated YouTube account information.

**Response:**
```json
{
  "authenticated": true,
  "channel": {
    "channel_id": "UC...",
    "title": "My Channel",
    "thumbnail_url": "https://...",
    "email": "user@example.com"
  }
}
```

#### POST `/api/youtube/login`
Authenticate with YouTube (triggers OAuth flow).

**Response:**
```json
{
  "message": "Successfully authenticated with YouTube",
  "channel": { ... }
}
```

#### POST `/api/youtube/logout`
Logout from YouTube (delete tokens).

**Response:**
```json
{
  "message": "Successfully logged out from YouTube"
}
```

### Schedule Management

#### GET `/api/schedule/next-available`
Get next available upload slot for video type.

**Parameters:**
- `video_type`: "final" or "short"

**Response:**
```json
{
  "next_available_time": "2025-10-25T10:00:00",
  "video_type": "final"
}
```

#### GET `/api/schedule/calendar`
Get scheduled uploads calendar view.

**Parameters:**
- `start_date`: ISO date string (optional)
- `days`: Number of days to show (default: 7)

**Response:**
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
Schedule video for upload at specific time.

**Request Body:**
```json
{
  "video_path": "/path/to/video.mp4",
  "video_type": "final",
  "publish_time": "2025-10-25T10:00:00" // optional
}
```

**Response:**
```json
{
  "message": "Video scheduled for 2025-10-25T10:00:00",
  "scheduled_time": "2025-10-25T10:00:00",
  "video_path": "/path/to/video.mp4",
  "video_type": "final"
}
```

### Quota Management

#### GET `/api/quota/status`
Get YouTube API quota usage status.

**Response:**
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

## Usage Examples

### Basic Upload Scheduling

```javascript
// Get next available time
const response = await fetch('/api/schedule/next-available?video_type=final');
const { next_available_time } = await response.json();

// Schedule video
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

### Custom Time Scheduling

```javascript
// Schedule for specific time
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

### Account Management

```javascript
// Login to YouTube
const loginResponse = await fetch('/api/youtube/login', {
  method: 'POST'
});

// Check account status
const accountResponse = await fetch('/api/youtube/account');
const { authenticated, channel } = await accountResponse.json();

// Logout
const logoutResponse = await fetch('/api/youtube/logout', {
  method: 'POST'
});
```

## Configuration

### Environment Variables

```bash
# YouTube API Configuration
YOUTUBE_CREDENTIALS_FILE=youtube_credentials.json
YOUTUBE_DAILY_LIMIT_FINAL=2
YOUTUBE_DAILY_LIMIT_SHORT=5
YOUTUBE_QUOTA_LIMIT=10000
YOUTUBE_WARNING_THRESHOLD=0.8
```

### Database Configuration

The system uses the following database tables:

- `youtube_schedule`: Scheduled uploads
- `youtube_accounts`: YouTube account information
- `youtube_quota_usage`: Daily quota tracking

### Scheduling Configuration

```python
# Default scheduling preferences
ScheduleConfig(
    daily_limits={'final': 2, 'short': 5},
    preferred_times=['10:00', '14:00', '18:00'],
    quota_limit=10000,
    warning_threshold=0.8
)
```

## Error Handling

### Common Error Responses

#### Authentication Errors
```json
{
  "error": "Authentication failed",
  "code": 401
}
```

#### Quota Exceeded
```json
{
  "error": "No remaining quota for final videos on 2025-10-25. Used: 2/2",
  "code": 400
}
```

#### Invalid Video Type
```json
{
  "error": "video_type must be 'final' or 'short'",
  "code": 400
}
```

#### Scheduling Conflicts
```json
{
  "error": "Requested time slot is occupied. Next available: 2025-10-25T14:00:00",
  "code": 400
}
```

## Best Practices

### 1. Quota Management
- Monitor quota usage regularly
- Schedule uploads during off-peak hours
- Use batch scheduling for multiple videos

### 2. Scheduling Strategy
- Plan uploads in advance
- Use preferred posting times
- Consider timezone differences

### 3. Error Handling
- Implement retry logic for failed uploads
- Monitor quota warnings
- Handle authentication failures gracefully

### 4. Performance
- Use async operations for API calls
- Cache account information
- Batch database operations

## Troubleshooting

### Common Issues

#### 1. Authentication Failures
- Verify OAuth credentials
- Check redirect URIs in Google Cloud Console
- Ensure test user permissions

#### 2. Quota Exceeded
- Check daily limits configuration
- Monitor API usage
- Implement quota warnings

#### 3. Scheduling Conflicts
- Use automatic scheduling
- Check existing schedules
- Verify timezone settings

#### 4. Upload Failures
- Check video file format
- Verify file permissions
- Monitor network connectivity

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('langflix.youtube').setLevel(logging.DEBUG)
```

## Security Considerations

### OAuth Security
- Store tokens securely
- Implement token refresh
- Use HTTPS for all communications

### Data Protection
- Encrypt sensitive data
- Implement access controls
- Regular security audits

### API Security
- Rate limiting
- Input validation
- Error message sanitization

## Monitoring and Analytics

### Key Metrics
- Upload success rate
- Quota utilization
- Scheduling accuracy
- User engagement

### Logging
- All API calls logged
- Error tracking
- Performance metrics
- User actions

## Future Enhancements

### Planned Features
- Bulk upload scheduling
- Advanced analytics
- A/B testing for metadata
- Integration with other platforms

### Performance Improvements
- Caching strategies
- Database optimization
- Async processing
- Load balancing

## Support

For technical support or feature requests, please refer to the project documentation or contact the development team.

---

*Last updated: October 2025*
