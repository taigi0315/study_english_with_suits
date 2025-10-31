---
applyTo: '**'
---

# General Agent Instructions

## Language & Communication
- **Queries**: Accept both English and Korean
- **Responses**: Respond in Korean for communication
- **Code**: Always write in English (variables, functions, comments)
- **Documentation**: Create bilingual versions
  - `filename_eng.md` - English version
  - `filename_kor.md` - Korean version

## Code Standards
- Write clear, descriptive comments in English
- Use meaningful variable and function names
- Follow existing code style and patterns
- Keep functions focused and single-purpose
- Document complex logic thoroughly

## Git Workflow
### For Implementation Work
1. Create feature branch: `feature/description` or `fix/description`
2. Commit incrementally with clear messages
3. When complete, create PR to `main` branch
4. Include summary of changes in PR description

### Branch Naming
- Features: `feature/ticket-number-brief-description`
- Fixes: `fix/ticket-number-brief-description`
- Refactoring: `refactor/ticket-number-brief-description`
- Documentation: `docs/description`

### Commit Messages
- Use clear, descriptive messages in English
- Format: `[type] brief description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

Example:
```
feat: add user authentication service
fix: resolve null pointer in payment handler
refactor: extract duplicate validation logic
docs: update API endpoint documentation
```

## File Organization
- Keep related files together
- Follow existing directory structure
- Update documentation when changing code
- Remove unused code and files

## Quality Principles
- **Clarity over cleverness**: Write code others can understand
- **Test what you build**: Ensure code is testable and tested
- **Document decisions**: Explain *why*, not just *what*
- **Review your work**: Check before committing
- **Ask when uncertain**: Clarify requirements before implementing

## Agent-Specific Notes
- Always read existing code/docs before making changes
- Maintain consistency with current patterns
- Consider impact on other parts of the system
- Follow the specific instructions for your role (Documentation Agent, Senior Engineer Agent, or Architect Agent)

---

**Remember: Write code for humans first, machines second.**