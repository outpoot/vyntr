# Contributing to Vyntr

Thank you for your interest in contributing to Vyntr! This document provides guidelines and workflows for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)
- [Community](#community)

## Code of Conduct

By participating in this project, you are expected to uphold our code of conduct:

- Be respectful and inclusive
- Exercise consideration and empathy
- Focus on collaborative problem-solving
- Gracefully accept constructive criticism
- Use welcoming and inclusive language

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up your development environment following the [ONBOARDING.md](ONBOARDING.md) guide
4. Create a new branch for your changes
5. Make your changes
6. Test thoroughly
7. Submit a pull request

## Development Process

### Branch Naming Convention

- `feature/`: For new features (e.g., `feature/unit-conversion`)
- `fix/`: For bug fixes (e.g., `fix/search-results-order`)
- `docs/`: For documentation changes (e.g., `docs/api-reference`)
- `refactor/`: For code refactoring (e.g., `refactor/crawler-module`)
- `perf/`: For performance improvements (e.g., `perf/embedding-generation`)
- `misc/`: For anything else (e.g., `misc/cleanup`)

### Commit Message Guidelines

Follow this convention for commit messages:
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Fix bug" not "Fixes bug")
- Have a short (50 characters or less) summary
- Include a longer description if necessary (wrap at 72 characters)
- Reference issues and pull requests in the footer
- Use the following format:

```
<module>(<component>): <short summary>

<optional longer description>

<optional footer(s)>
```

Example:
```
website(feat): add currency conversion feature

This feature allows users to convert between different currencies and
displays the results in real-time.

Fixes #123
```

## Pull Request Process

1. Update relevant documentation with details of changes
2. Ensure all tests pass
3. Make sure your code follows the project's coding standards
4. Submit the pull request with a clear title and description
5. Address any feedback from code reviewers
6. Once approved, a maintainer will merge your PR

## Coding Standards

### Rust (Genesis & Pulse)
- Follow the Rust Style Guide
- Use `cargo fmt` to format code
- Use `cargo clippy` to catch common mistakes

### TypeScript/JavaScript (Website)
- Use TypeScript for type safety
- Document complex functions and components
- Follow the component structure in the existing codebase

### Python (Tools)
- Follow PEP 8 style guidelines
- Use type hints
- Document functions and classes with docstrings

## Testing Guidelines

### What to Test
- Core functionality
- Edge cases
- Performance critical paths
- Regression tests for fixed bugs

## Documentation

- Update relevant README files when adding or modifying features
- Document API endpoints with examples
- Add inline code comments for complex logic
- Keep the wiki updated with architectural decisions

## Issue Reporting

When reporting issues, please include:

1. Steps to reproduce the bug
2. Expected behavior
3. Actual behavior
4. Screenshots or error logs if applicable
5. Environment details (OS, browser, etc.)
6. Possible solutions if you have ideas

Use the following issue templates:
- Bug report: For reporting bugs
- Feature request: For suggesting new features
- Documentation improvement: For suggesting documentation changes

## Component-Specific Guidelines

### Genesis (Crawler)
- Monitor resource usage (memory, network)
- Document any changes to the data format

### Website (Frontend)
- Follow accessibility best practices
- Test across different browsers and devices
- Optimize for performance (bundle size, rendering)

### Pulse (Search)
- Benchmark search performance
- Document indexing strategies
- Test with realistic data volumes

### Lexicon (Dictionary)
- Maintain compatibility with WordNet data format
- Test API endpoints
- Document any schema changes

## Licensing

- Code contributions must be licensed under the project's CC BY-NC 4.0 license