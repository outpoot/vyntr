# Vyntr Contribution Guidelines

## Branch Naming Convention
- `feature/`: For new features (e.g., `feature/unit-conversion`)
- `fix/`: For bug fixes (e.g., `fix/search-results-order`)
- `docs/`: For documentation changes (e.g., `docs/api-reference`)
- `refactor/`: For code refactoring (e.g., `refactor/crawler-module`)
- `perf/`: For performance improvements (e.g., `perf/embedding-generation`)
- `misc/`: For anything else (e.g., `misc/cleanup`)

## Commit Message Format
```
<module>(<component>): <short summary>

<optional longer description>

<optional footer(s)>
```

Examples:
```
website(feat): add currency conversion feature

This feature allows users to convert between different currencies and
displays the results in real-time.

Fixes #123
```

## Pull Request Process
1. Update documentation with details of changes
2. Ensure all tests pass
3. Follow coding standards
4. Submit PR with clear title and description
5. Address any feedback from code reviewers

## Testing Guidelines
- Test core functionality
- Cover edge cases
- Include performance tests for critical paths
- Add regression tests for fixed bugs