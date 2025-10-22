# ADR-013: Expression Configuration Architecture

**Date:** 2025-01-27  
**Status:** Accepted  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation), ADR-010 (Database Schema Design)

## Context

LangFlix is implementing expression-based learning features as outlined in the north-start-doc.md development plan. This requires a comprehensive configuration system to manage:

- Subtitle styling for expression highlighting
- Video playback settings (repetition, transitions)
- Layout configurations for different video formats (landscape/portrait)
- LLM and WhisperX integration settings

The existing LangFlix system already has a robust configuration management system using YAML files and ConfigLoader, but it needs to be extended to support the new expression-based learning features.

## Decision

We will extend the existing configuration system with expression-specific settings while maintaining consistency with the current architecture:

### 1. Configuration Structure

**Expression Configuration Classes:**
- `SubtitleStylingConfig`: Manages subtitle appearance (default and highlight styles)
- `PlaybackConfig`: Controls video repetition and transition settings
- `LayoutConfig`: Defines layout for landscape and portrait video formats
- `ExpressionConfig`: Main configuration class that combines all settings

**Configuration Hierarchy:**
```
ExpressionConfig
├── SubtitleStylingConfig
│   ├── default (dict)
│   └── expression_highlight (dict)
├── PlaybackConfig
│   ├── expression_repeat_count
│   ├── context_play_count
│   ├── repeat_delay_ms
│   ├── transition_effect
│   └── transition_duration_ms
├── LayoutConfig
│   ├── landscape (dict)
│   └── portrait (dict)
├── llm (dict)
└── whisper (dict)
```

### 2. Database Schema Extension

**New Expression Fields:**
- `difficulty` (Integer): 1-10 difficulty level
- `category` (String(50)): Expression category (idiom, slang, formal, etc.)
- `educational_value` (Text): Explanation of learning value
- `usage_notes` (Text): Additional usage context
- `score` (Float): Ranking score for expression selection

### 3. Settings Integration

**New Settings Accessors:**
- `get_expression_config()`: Get entire expression configuration
- `get_expression_subtitle_styling()`: Get subtitle styling settings
- `get_expression_playback()`: Get playback configuration
- `get_expression_layout()`: Get layout settings
- `get_expression_llm()`: Get LLM configuration
- `get_expression_whisper()`: Get WhisperX configuration

### 4. YAML Configuration

**Default Configuration Structure:**
```yaml
expression:
  subtitle_styling:
    default:
      color: '#FFFFFF'
      font_family: 'Arial'
      font_size: 24
      # ... other default styling
    expression_highlight:
      color: '#FFD700'
      font_weight: 'bold'
      # ... highlight styling
  playback:
    expression_repeat_count: 2
    context_play_count: 1
    # ... other playback settings
  layout:
    landscape:
      resolution: [1920, 1080]
      # ... landscape layout
    portrait:
      resolution: [1080, 1920]
      # ... portrait layout
  llm:
    provider: gemini
    model: gemini-1.5-pro
    # ... LLM settings
  whisper:
    model_size: base
    device: cpu
    # ... WhisperX settings
```

## Rationale

### Why Extend Existing System

1. **Consistency**: Maintains the same configuration patterns used throughout LangFlix
2. **Familiarity**: Developers already understand the ConfigLoader pattern
3. **Environment Override Support**: Leverages existing environment variable override system
4. **Validation**: Reuses existing configuration validation patterns

### Why Dataclass Structure

1. **Type Safety**: Provides compile-time type checking
2. **Default Values**: Built-in support for default values with `field(default_factory=dict)`
3. **Validation**: Easy to add custom validation logic
4. **Serialization**: Simple conversion to/from dictionaries

### Why Database Schema Extension

1. **Backward Compatibility**: Existing Expression records remain valid
2. **Gradual Migration**: New fields are nullable, allowing gradual adoption
3. **Query Flexibility**: New fields enable advanced filtering and sorting
4. **Future-Proof**: Extensible design for additional learning features

## Consequences

### Positive

- **Unified Configuration**: Single source of truth for all expression settings
- **Type Safety**: Compile-time validation of configuration values
- **Environment Flexibility**: Easy override via environment variables
- **Database Compatibility**: Seamless integration with existing data
- **Testing**: Comprehensive test coverage for all configuration scenarios

### Negative

- **Migration Required**: Database migration needed for new fields
- **Configuration Complexity**: More configuration options to manage
- **Learning Curve**: Developers need to understand new configuration structure

### Risks

- **Breaking Changes**: Configuration changes could affect existing functionality
- **Migration Issues**: Database migration could fail in production
- **Performance**: Additional fields could impact query performance

### Mitigation

- **Comprehensive Testing**: Unit and integration tests for all components
- **Backward Compatibility**: New fields are nullable and optional
- **Documentation**: Clear documentation of all configuration options
- **Gradual Rollout**: Phased deployment with monitoring

## Implementation Details

### Files Created/Modified

**New Files:**
- `langflix/config/expression_config.py`: Configuration dataclasses
- `langflix/db/migrations/versions/0002_add_expression_fields.py`: Database migration
- `tests/unit/test_expression_config.py`: Unit tests
- `tests/integration/test_expression_db_migration.py`: Integration tests

**Modified Files:**
- `langflix/config/default.yaml`: Added expression configuration section
- `langflix/settings.py`: Added expression accessor functions
- `langflix/db/models.py`: Extended Expression model with new fields
- `langflix/core/models.py`: Extended ExpressionAnalysis with new fields

### Configuration Validation

**Built-in Validation:**
- Difficulty range: 1-10
- Positive values for counts and delays
- Valid resolution arrays: [width, height]
- Required dictionary structures

**Custom Validation:**
- Layout resolution format validation
- Subtitle styling structure validation
- Playback setting range validation

### Database Migration

**Migration Strategy:**
1. Add new nullable columns
2. Update existing records with default values
3. Add constraints if needed
4. Update application code to handle new fields

**Rollback Plan:**
- Migration can be reversed by dropping new columns
- Application code gracefully handles missing fields
- No data loss during rollback

## Testing Strategy

### Unit Tests
- Configuration class instantiation
- Default value validation
- Custom value handling
- Validation error detection
- Settings accessor functions

### Integration Tests
- Database migration execution
- CRUD operations with new fields
- Configuration loading from YAML
- Environment variable overrides

### Performance Tests
- Configuration loading performance
- Database query performance with new fields
- Memory usage with large configurations

## Future Considerations

### Phase 2 Extensions
- Advanced LLM prompt templates
- Custom subtitle styling themes
- Dynamic layout generation
- A/B testing for configuration values

### Monitoring
- Configuration usage analytics
- Performance impact monitoring
- Error rate tracking for new features

### Documentation
- Configuration reference guide
- Best practices documentation
- Troubleshooting guide

## References

- [north-start-doc.md](../north-start-doc.md): Original development plan
- [ADR-009](ADR-009-service-architecture-foundation.md): Service architecture foundation
- [ADR-010](ADR-010-database-schema-design.md): Database schema design
- [LangFlix Configuration Guide](../../en/USER_MANUAL.md#configuration): User configuration guide
