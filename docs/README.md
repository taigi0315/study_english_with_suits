# LangFlix Documentation

This directory contains all documentation for the LangFlix project, organized by language and type.

## 📁 Directory Structure

```
docs/
├── en/                     # English documentation
│   ├── USER_MANUAL.md      # Complete usage guide
│   ├── API_REFERENCE.md    # Developer API reference
│   ├── TROUBLESHOOTING.md  # Common issues and solutions
│   ├── DEPLOYMENT.md       # Production setup guide
│   ├── PERFORMANCE.md      # Optimization tips
│   └── CONTRIBUTING.md     # Contribution guidelines
├── ko/                     # Korean documentation (한국어)
│   ├── USER_MANUAL_KOR.md      # 완전한 사용 가이드
│   ├── API_REFERENCE_KOR.md    # 개발자 API 참조
│   ├── TROUBLESHOOTING_KOR.md  # 일반적인 문제와 해결책
│   ├── DEPLOYMENT_KOR.md       # 프로덕션 설정 가이드
│   ├── PERFORMANCE_KOR.md      # 최적화 팁
│   └── CONTRIBUTING_KOR.md     # 기여 가이드라인
├── adr/                    # Architecture Decision Records
│   ├── ADR-005-gemini-tts-integration.md
│   ├── ADR-006-short-video-architecture.md
│   ├── ADR-007-direct-ssml-configuration.md
│   └── ADR-008-cursor-build-mode-instructions.md
├── development_diary.md    # Project development history
├── system_design_and_development_plan.md  # Technical architecture
└── README.md              # This file
```

## 📚 Documentation Types

### User Documentation
- **User Manual**: Complete usage guide for end users
- **Troubleshooting**: Common issues and their solutions
- **Setup Guide**: Installation and configuration instructions

### Developer Documentation
- **API Reference**: Programmatic usage and integration
- **System Design**: Technical architecture and design decisions
- **Development Diary**: Project history and milestones

### Operational Documentation
- **Deployment Guide**: Production setup and deployment
- **Performance Guide**: Optimization tips and best practices
- **Contributing Guide**: Guidelines for contributors

### Architecture Documentation
- **ADR (Architecture Decision Records)**: Key architectural decisions
- **System Design**: High-level technical architecture

## 🌐 Language Support

LangFlix documentation is available in two languages:

- **English** (`docs/en/`): Primary documentation language
- **Korean** (`docs/ko/`): 한국어 문서

Both language versions are kept synchronized and contain the same information.

## 📖 Quick Navigation

### For Users
- [English User Manual](en/USER_MANUAL.md)
- [한국어 사용자 매뉴얼](ko/USER_MANUAL_KOR.md)
- [English Troubleshooting](en/TROUBLESHOOTING.md)
- [한국어 문제 해결 가이드](ko/TROUBLESHOOTING_KOR.md)

### For Developers
- [English API Reference](en/API_REFERENCE.md)
- [한국어 API 참조](ko/API_REFERENCE_KOR.md)
- [System Design](system_design_and_development_plan.md)
- [Development Diary](development_diary.md)

### For DevOps
- [English Deployment Guide](en/DEPLOYMENT.md)
- [한국어 배포 가이드](ko/DEPLOYMENT_KOR.md)
- [English Performance Guide](en/PERFORMANCE.md)
- [한국어 성능 가이드](ko/PERFORMANCE_KOR.md)

### For Contributors
- [English Contributing Guide](en/CONTRIBUTING.md)
- [한국어 기여 가이드](ko/CONTRIBUTING_KOR.md)

## 🔄 Documentation Maintenance

### Updating Documentation
When updating documentation:

1. **Update both language versions** (English and Korean)
2. **Maintain consistency** between language versions
3. **Update cross-references** in other documents
4. **Test all links** to ensure they work correctly
5. **Update the main README.md** if needed

### Adding New Documentation
When adding new documentation:

1. **Choose appropriate language directory** (`en/` or `ko/`)
2. **Follow naming conventions** (e.g., `FEATURE_NAME.md`)
3. **Add cross-references** in related documents
4. **Update this README.md** with new document links
5. **Update main project README.md** if it's user-facing

### Architecture Decision Records (ADR)
When creating new ADRs:

1. **Use sequential numbering** (ADR-009, ADR-010, etc.)
2. **Follow the ADR template** structure
3. **Include context, decision, and consequences**
4. **Reference related ADRs** when applicable
5. **Update the ADR index** if one exists

## 📝 Documentation Standards

### Writing Guidelines
- **Clear and concise**: Use simple, direct language
- **Consistent terminology**: Use the same terms throughout
- **Code examples**: Include working code examples
- **Screenshots**: Use screenshots for UI-related documentation
- **Cross-references**: Link to related documentation

### Formatting Standards
- **Markdown**: Use standard Markdown formatting
- **Headers**: Use consistent header hierarchy
- **Code blocks**: Use appropriate language tags
- **Links**: Use relative paths for internal links
- **Tables**: Use Markdown tables for structured data

### Review Process
- **Technical accuracy**: Ensure all technical information is correct
- **Language consistency**: Check for consistent terminology
- **Link validation**: Verify all links work correctly
- **User testing**: Test documentation with actual users when possible

## 🤝 Contributing to Documentation

### How to Contribute
1. **Fork the repository**
2. **Create a feature branch** for documentation changes
3. **Make your changes** following the standards above
4. **Test your changes** by building the documentation
5. **Submit a pull request** with a clear description

### What to Contribute
- **Bug fixes**: Correct errors in existing documentation
- **Updates**: Keep documentation current with code changes
- **Improvements**: Enhance clarity and usability
- **Translations**: Help maintain Korean documentation
- **New content**: Add missing documentation

## 📞 Getting Help

If you need help with documentation:

1. **Check existing documentation** first
2. **Search for similar issues** in the repository
3. **Create an issue** with specific questions
4. **Contact the maintainers** for complex issues

---

**Last Updated:** October 21, 2025  
**Maintainer:** LangFlix Development Team