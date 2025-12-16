# LangFlix Quick Reference Guide

> **Visual workflows for common tasks**

## 📋 Table of Contents
- [Pipeline Workflows](#pipeline-workflows)
- [Component Usage](#component-usage)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Pipeline Workflows

### Running the Complete Pipeline

```mermaid
flowchart TD
    START([▶️ Start]) --> A{Have<br/>Video + Subtitles?}

    A -->|✅ Yes| B[📁 Prepare Files]
    A -->|❌ No| C[❌ Get Netflix content first]

    B --> D[🔧 Configure Settings<br/>config/default.yaml]
    D --> E[🚀 Run Pipeline]

    E --> F{Mode?}
    F -->|CLI| G[python -m langflix.main<br/>--video S01E01.mp4<br/>--subtitles S01E01/]
    F -->|Web UI| H[python -m langflix.youtube.web_ui<br/>http://localhost:5000]

    G --> I[⏳ Processing...]
    H --> I

    I --> J[🎬 Long-Form Videos<br/>16:9]
    I --> K[📱 Short-Form Videos<br/>9:16]

    J --> L[☁️ YouTube Upload]
    K --> L

    L --> M([✅ Complete])

    C --> STOP([🛑 Stop])

    style START fill:#e8f5e9
    style B fill:#e1f5ff
    style D fill:#fff4e6
    style E fill:#f3e5f5
    style J fill:#e8f5e9
    style K fill:#e8f5e9
    style M fill:#e8f5e9
    style STOP fill:#ffebee
```

### File Preparation Workflow

```mermaid
flowchart LR
    A[📺 Netflix Episode<br/>S01E01.mp4] --> B[📁 Create Folder Structure]

    B --> C{Subtitle<br/>Format?}

    C -->|Netflix Folder| D1[S01E01/<br/>├── 7_English.srt<br/>├── 4_Korean.srt<br/>└── 13_Spanish.srt]

    C -->|Single File| D2[S01E01.ko.srt<br/>S01E01.es.srt]

    D1 --> E[🔧 Enable dual_language<br/>in config]
    D2 --> E

    E --> F[⚙️ Set source_language<br/>e.g., "Korean"]
    F --> G[⚙️ Set target_language<br/>e.g., "Spanish"]

    G --> H[✅ Ready to Run]

    style A fill:#e1f5ff
    style E fill:#fff4e6
    style F fill:#fff4e6
    style G fill:#fff4e6
    style H fill:#e8f5e9
```

---

## Component Usage

### Using PathResolver

```mermaid
flowchart TD
    A[Need File Path?] --> B[Initialize PathResolver]

    B --> C[PathResolver<br/>output_dir="workspace/korean/long_form_videos"]

    C --> D{What Path<br/>Type?}

    D -->|Short Videos| E1[get_shorts_dir]
    D -->|Subtitles| E2[get_subtitles_dir]
    D -->|Temp Files| E3[get_temp_path<br/>prefix, identifier]
    D -->|Long Videos| E4[get_long_form_path<br/>expression, index]

    E1 --> F1[📁 workspace/korean/shorts/]
    E2 --> F2[📁 workspace/korean/subtitles/]
    E3 --> F3[📁 workspace/korean/long_form_videos/<br/>temp_context_clip_hello.mkv]
    E4 --> F4[📁 workspace/korean/long_form_videos/<br/>01_hello.mkv]

    style B fill:#fff4e6
    style F1 fill:#e8f5e9
    style F2 fill:#e8f5e9
    style F3 fill:#e8f5e9
    style F4 fill:#e8f5e9
```

### Using FontResolver

```mermaid
flowchart TD
    A[Need Font?] --> B[Initialize FontResolver]

    B --> C[FontResolver<br/>target_language="es"<br/>source_language="ko"]

    C --> D{Font<br/>Type?}

    D -->|Source Only| E1[get_source_font<br/>use_case="expression"]
    D -->|Target Only| E2[get_target_font<br/>use_case="translation"]
    D -->|Both| E3[get_dual_fonts<br/>use_case="vocabulary"]

    E1 --> F1[🔤 Korean Font<br/>/path/to/korean.ttf]
    E2 --> F2[🔤 Spanish Font<br/>/path/to/spanish.ttf]
    E3 --> F3[🔤 Both Fonts<br/>korean.ttf, spanish.ttf]

    F1 --> G[Use in FFmpeg<br/>drawtext filter]
    F2 --> G
    F3 --> G

    G --> H[✅ Rendered Text]

    style B fill:#fff4e6
    style G fill:#f3e5f5
    style H fill:#e8f5e9
```

### Creating Short-Form Videos

```mermaid
flowchart TD
    A[Have Long-Form Video?] --> B[Initialize ShortFormCreator]

    B --> C[ShortFormCreator<br/>source_lang="ko"<br/>target_lang="es"]

    C --> D[create_short_form_from_long_form<br/>long_form_path<br/>expression<br/>expression_index]

    D --> E[⚖️ Scale to 1080x1920]
    E --> F[⬛ Add Black Padding<br/>440px top/bottom]

    F --> G{Add Overlays}

    G --> H1[📌 Viral Title]
    G --> H2[🏷️ Keywords]
    G --> H3[📚 Vocabulary]
    G --> H4[💭 Narrations]
    G --> H5[🗣️ Expression Text]

    H1 --> I[🎨 Add Logo]
    H2 --> I
    H3 --> I
    H4 --> I
    H5 --> I

    I --> J[📝 Embed Subtitles]
    J --> K[✅ Short-Form Video<br/>1080x1920]

    style B fill:#fff4e6
    style D fill:#f3e5f5
    style K fill:#e8f5e9
```

---

## Common Tasks

### Task 1: Generate Videos for One Episode

```mermaid
sequenceDiagram
    participant You
    participant CLI
    participant Pipeline
    participant Output

    You->>CLI: python -m langflix.main<br/>--video S01E01.mp4<br/>--subtitles S01E01/<br/>--episode S01E01

    CLI->>Pipeline: Start Processing

    Note over Pipeline: 1. Parse Subtitles<br/>2. Analyze Expressions<br/>3. Extract Clips<br/>4. Generate Videos

    Pipeline->>Output: Long-form videos<br/>workspace/korean/long_form_videos/

    Pipeline->>Output: Short-form videos<br/>workspace/korean/shorts/

    Output->>You: ✅ Videos Ready

    Note over You: Videos saved to workspace/
```

### Task 2: Upload Videos to YouTube

```mermaid
flowchart TD
    A[Videos Generated] --> B{Upload<br/>Method?}

    B -->|Web UI| C1[Open http://localhost:5000/upload]
    B -->|API| C2[POST /api/v1/upload]
    B -->|CLI| C3[python -m langflix.upload<br/>--video path.mkv]

    C1 --> D[Select Video Files]
    C2 --> D
    C3 --> D

    D --> E[Configure Metadata<br/>Title, Description, Tags]

    E --> F[🔐 Authenticate YouTube]

    F --> G[☁️ Upload to YouTube]

    G --> H{Upload<br/>Success?}

    H -->|✅ Yes| I[💾 Save to Database]
    H -->|❌ No| J[🔄 Retry or Check Logs]

    I --> K[✅ Video Live on YouTube]

    style A fill:#e1f5ff
    style F fill:#fff4e6
    style G fill:#f3e5f5
    style K fill:#e8f5e9
    style J fill:#ffebee
```

### Task 3: Configure for New Language Pair

```mermaid
flowchart TD
    A[Want New Language Pair?] --> B[Edit config/default.yaml]

    B --> C[Set source_language<br/>e.g., "ja" for Japanese]

    C --> D[Set target_language<br/>e.g., "en" for English]

    D --> E[Test Font Support]

    E --> F[python scripts/test_font_resolution.py]

    F --> G{Fonts<br/>Available?}

    G -->|✅ Yes| H[Run Pipeline]
    G -->|❌ No| I[Install Missing Fonts]

    I --> E

    H --> J[✅ Videos with New Languages]

    style B fill:#fff4e6
    style C fill:#fff4e6
    style D fill:#fff4e6
    style F fill:#f3e5f5
    style J fill:#e8f5e9
```

---

## Troubleshooting

### Video Processing Issues

```mermaid
flowchart TD
    A[❌ Video Processing Failed] --> B{Error<br/>Type?}

    B -->|FFmpeg Error| C1[Check FFmpeg installed<br/>ffmpeg -version]
    B -->|Font Error| C2[Run font test<br/>test_font_resolution.py]
    B -->|File Not Found| C3[Check file paths<br/>Verify structure]
    B -->|Memory Error| C4[Reduce parallel workers<br/>Check available RAM]

    C1 --> D1{FFmpeg<br/>Installed?}
    D1 -->|❌ No| E1[Install FFmpeg<br/>brew install ffmpeg]
    D1 -->|✅ Yes| F1[Check FFmpeg logs<br/>langflix.log]

    C2 --> D2{Fonts<br/>Found?}
    D2 -->|❌ No| E2[Install fonts<br/>See font_resolver_guide.md]
    D2 -->|✅ Yes| F2[Check font permissions]

    C3 --> D3{Files<br/>Exist?}
    D3 -->|❌ No| E3[Correct file paths<br/>Use absolute paths]
    D3 -->|✅ Yes| F3[Check file permissions]

    C4 --> D4{RAM<br/>Sufficient?}
    D4 -->|❌ No| E4[Reduce workers<br/>max_workers=1]
    D4 -->|✅ Yes| F4[Check temp space<br/>Clean temp files]

    E1 --> G[✅ Retry]
    E2 --> G
    E3 --> G
    E4 --> G
    F1 --> G
    F2 --> G
    F3 --> G
    F4 --> G

    style A fill:#ffebee
    style G fill:#e8f5e9
```

### LLM API Issues

```mermaid
flowchart TD
    A[❌ LLM API Failed] --> B{Error<br/>Type?}

    B -->|Rate Limit| C1[💤 Wait & Retry<br/>Exponential backoff]
    B -->|Invalid API Key| C2[🔑 Check API Key<br/>GEMINI_API_KEY env var]
    B -->|No Response| C3[🌐 Check Network<br/>Firewall/Proxy]
    B -->|Invalid Format| C4[📝 Check Prompt<br/>Validate JSON]

    C1 --> D1[⏱️ Wait 60 seconds]
    D1 --> E[🔄 Retry Request]

    C2 --> D2[Verify .env file<br/>GEMINI_API_KEY=xxx]
    D2 --> E

    C3 --> D3[Test API directly<br/>curl https://generativelanguage...]
    D3 --> E

    C4 --> D4[Review expression_analysis_prompt<br/>Check JSON schema]
    D4 --> E

    E --> F{Success?}
    F -->|✅ Yes| G[✅ Continue Pipeline]
    F -->|❌ No| H[📧 Check Logs<br/>Contact Support]

    style A fill:#ffebee
    style E fill:#fff4e6
    style G fill:#e8f5e9
```

### Upload Failures

```mermaid
flowchart TD
    A[❌ YouTube Upload Failed] --> B{Error<br/>Type?}

    B -->|Auth Error| C1[🔐 Re-authenticate<br/>Delete credentials.json]
    B -->|Quota Exceeded| C2[⏰ Wait for Reset<br/>Daily quota: 10K units]
    B -->|Video Too Large| C3[📏 Check File Size<br/>Max: 256GB]
    B -->|Invalid Metadata| C4[📝 Validate Fields<br/>Title, Description]

    C1 --> D1[python -m langflix.youtube.auth]
    D1 --> E[🔄 Retry Upload]

    C2 --> D2[⏱️ Wait 24 hours<br/>Or use different account]
    D2 --> E

    C3 --> D3[🗜️ Re-encode Video<br/>Lower bitrate/resolution]
    D3 --> E

    C4 --> D4[✏️ Fix Metadata<br/>Remove special chars]
    D4 --> E

    E --> F{Success?}
    F -->|✅ Yes| G[✅ Video Live]
    F -->|❌ No| H[📧 Check YouTube API Logs]

    style A fill:#ffebee
    style E fill:#fff4e6
    style G fill:#e8f5e9
```

---

## Quick Command Reference

### CLI Commands

```bash
# Run complete pipeline
python -m langflix.main \\
    --video S01E01.mp4 \\
    --subtitles S01E01/ \\
    --episode S01E01 \\
    --language korean

# Start web dashboard
python -m langflix.youtube.web_ui

# Run API server
python -m langflix.api.main

# Test font resolution
python scripts/test_font_resolution.py

# Clean temp files
python -m langflix.utils.cleanup --temp-only
```

### Configuration Paths

```yaml
# config/default.yaml

# Dual-language settings
dual_language:
  enabled: true
  source_language: "Korean"    # Language to learn
  target_language: "Spanish"   # User's language

# Video settings
video:
  short_video:
    width: 1080
    height: 1920
  long_video:
    width: 1920
    height: 1080

# LLM settings
llm:
  provider: "gemini"
  model_name: "gemini-2.5-flash"
```

### Directory Locations

```
workspace/
└── korean/                    # Language directory
    ├── long_form_videos/      # 16:9 videos
    ├── shorts/                # 9:16 videos
    ├── expressions/           # Expression clips
    ├── subtitles/             # SRT files
    ├── tts_audio/             # TTS cache
    └── videos/                # Source videos
```

---

## Performance Tips

### Optimize Pipeline Speed

```mermaid
flowchart TD
    A[🚀 Speed Up Pipeline?] --> B{Bottleneck?}

    B -->|Video Processing| C1[✅ Enable Parallel Processing<br/>max_workers=4]
    B -->|LLM API Calls| C2[✅ Reduce max_input_length<br/>2000 → 1500]
    B -->|File I/O| C3[✅ Use SSD Storage<br/>Fast temp directory]
    B -->|Memory Usage| C4[✅ Clear Cache Regularly<br/>Clean temp files]

    C1 --> D[⚡ 4x Faster]
    C2 --> E[⚡ Fewer API Calls]
    C3 --> F[⚡ Faster Read/Write]
    C4 --> G[⚡ More Available RAM]

    D --> H[✅ Optimized Pipeline]
    E --> H
    F --> H
    G --> H

    style A fill:#e1f5ff
    style H fill:#e8f5e9
```

### Cache Strategy

```mermaid
flowchart LR
    A[📊 Data Request] --> B{Cache?}

    B -->|TTS Audio| C1[💾 CacheManager<br/>Disk]
    B -->|Fonts| C2[💾 FontResolver<br/>Memory]
    B -->|Expressions| C3[💾 Redis<br/>Distributed]

    C1 --> D1[⚡ Fast Retrieval<br/>No TTS generation]
    C2 --> D2[⚡ Instant Access<br/>No file lookup]
    C3 --> D3[⚡ Shared Cache<br/>Multi-process]

    D1 --> E[✅ Performance Boost]
    D2 --> E
    D3 --> E

    style B fill:#fff4e6
    style E fill:#e8f5e9
```

---

## Related Documentation

- **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)** - Complete system architecture with diagrams
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - V2 dual-language architecture
- **[font_resolver_guide.md](./font_resolver_guide.md)** - FontResolver API reference
- **[font_configuration_examples.md](./font_configuration_examples.md)** - Font configuration examples
- **[CONFIGURATION.md](./CONFIGURATION.md)** - Configuration reference

---

**Last Updated**: 2025-12-16
**Version**: 2.0
