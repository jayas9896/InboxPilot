# Coding Standards

## Documentation Comments
- Every module, class, and function must include a docstring.
- Each docstring must include:
  - Summary: what the element does.
  - Importance: why it exists or the role it plays.
  - Alternatives: a brief note about a reasonable alternative approach.

## Style and Linting
- Use Ruff for static analysis and style checks.
- Enforce docstring presence and basic safety checks.

## Testing
- Use pytest for automated tests.
- Add tests for core logic (categories, classification, AI abstraction, and integrations via mocks).

## Security
- Do not log secrets.
- Load credentials and tokens from environment variables or local secret stores.

## Git Discipline
- Every logical change set requires a new CL ID and detailed change log entry.
- Keep commits small and focused.
