# Educational Video Terminology

## 📚 **LangFlix Educational Video Components**

### **1. Context Video (컨텍스트 비디오)**
- **Definition**: Original video clip with dual-language subtitles
- **Purpose**: Provides context and background for the expression
- **Features**: 
  - Original dialogue with Korean translation
  - Full scene context for understanding
  - Duration: 6-22 seconds (varies by expression)

### **2. Expression Repeat Clip (표현 반복 클립)**
- **Definition**: Short clip containing only the expression, repeated 3 times
- **Purpose**: Focused learning of the specific expression
- **Features**:
  - Audio plays 3 times for reinforcement
  - Visual focus on the expression moment
  - Duration: Original expression length × 3

### **3. Educational Slide (교육용 슬라이드)**
- **Definition**: Static slide with expression text and translation
- **Purpose**: Visual reinforcement and memorization
- **Features**:
  - Black background for focus
  - Large expression text (white, 48px)
  - Translation text (yellow, 32px)
  - Duration: Audio length + 3 seconds

## 🎬 **Educational Video Sequence Structure**

```
Context Video → Expression Repeat Clip → Educational Slide
     ↓                    ↓                      ↓
[Full scene with      [Expression only,      [Text display with
 subtitles]           repeated 3x]          audio + 3s pause]
```

## 📖 **Technical Terms**

### **Video Processing Terms:**
- **Context Video**: 비디오 클립 + 자막
- **Expression Repeat**: 표현 부분만 3회 반복
- **Educational Slide**: 교육용 슬라이드
- **Final Sequence**: 최종 교육용 비디오

### **Learning Components:**
- **Context Learning**: 상황 이해를 위한 전체 장면
- **Expression Focus**: 표현 집중 학습
- **Visual Reinforcement**: 시각적 강화 학습

## 🎯 **Educational Benefits**

### **Multi-Modal Learning:**
1. **Visual Context**: Full scene understanding
2. **Audio Repetition**: 3x audio reinforcement
3. **Text Display**: Visual text memorization
4. **Progressive Learning**: Context → Focus → Reinforcement

### **Learning Flow:**
1. **Understand**: Context video shows full situation
2. **Focus**: Expression repeat highlights key phrase
3. **Memorize**: Educational slide reinforces learning
4. **Repeat**: Process continues for next expression

## 📝 **Implementation Notes**

### **Duration Calculations:**
- **Context Video**: Original clip duration
- **Expression Repeat**: Original duration × 3
- **Educational Slide**: Audio duration + 3 seconds
- **Total per expression**: Context + Repeat + Slide

### **Quality Settings:**
- **Video Codec**: H.264 (libx264)
- **Audio Codec**: AAC
- **Resolution**: 1280x720 (HD)
- **Frame Rate**: 23.98 fps (consistent)
- **Audio**: Stereo (converted from 5.1)

## 🌍 **Multi-Language Support**

### **Supported Languages:**
- **ko**: Korean (한국어)
- **ja**: Japanese (日本語)
- **zh**: Chinese (中文)
- **es**: Spanish (Español)
- **fr**: French (Français)

### **Language-Specific Features:**
- **Font Support**: Each language has optimized font paths
- **Translation Quality**: Natural, contextual translations
- **Character Encoding**: UTF-8 support for all languages
- **Prompt Localization**: Language-specific prompt templates

### **Folder Structure for Multi-Language:**
```
output/
├── Series/
│   ├── Episode/
│   │   ├── shared/           # Language-independent resources
│   │   ├── translations/     # Language-specific content
│   │   │   ├── ko/          # Korean
│   │   │   ├── ja/          # Japanese
│   │   │   ├── zh/          # Chinese
│   │   │   ├── es/          # Spanish
│   │   │   └── fr/          # French
│   │   └── metadata/        # Common metadata
```

This terminology ensures clear communication about the educational video components and their purposes in the LangFlix learning system.
