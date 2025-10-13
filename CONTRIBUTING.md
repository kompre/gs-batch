# Contributing to gs-batch-pdf

Thank you for your interest in contributing to gs-batch-pdf!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kompre/gs-batch.git
   cd gs-batch
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync --all-extras
   ```

3. **Install Ghostscript** (required for tests)
   - **macOS**: `brew install ghostscript`
   - **Linux**: `sudo apt-get install ghostscript`
   - **Windows**: Download from [ghostscript.com](https://www.ghostscript.com/)

4. **Run tests**
   ```bash
   uv run pytest
   ```

5. **Run type checking**
   ```bash
   uv run mypy gs_batch/
   ```

## Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

3. Push and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

## Pull Request Guidelines

- Write clear, descriptive commit messages
- Add tests for new functionality
- Ensure all tests pass (`uv run pytest`)
- Update documentation as needed
- Follow existing code style and conventions

## Release Process

Releases are automated through GitHub Actions. Only maintainers can create releases.

### For Maintainers: Creating a Release

1. **Create a release PR** with version bump:
   ```bash
   git checkout -b release/v0.5.7
   ```

2. **Update version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.5.7"  # Bump from previous version
   ```

3. **Write a comprehensive PR description** (becomes release notes):
   ```markdown
   Title: Release v0.5.7: Brief description of changes

   ## Summary
   High-level overview of what changed in this release.

   ## Changes
   - Feature: Add new functionality X
   - Fix: Resolve issue with Y
   - Enhancement: Improve performance of Z

   ## Breaking Changes
   None (or describe any breaking changes)

   ## Migration Notes
   Steps users need to take to upgrade (if any)
   ```

4. **Create the pull request** on GitHub

5. **Add the "release" label** to the PR
   - In GitHub UI, add label: `release`
   - This marks it for automatic publishing

6. **Get approval and merge**
   - CI will run all tests
   - Once approved, merge the PR

7. **Automated publishing** (happens automatically after merge):
   - ✅ Workflow reads version from `pyproject.toml`
   - ✅ Creates Git tag (e.g., `v0.5.7`)
   - ✅ Builds wheel and source distribution
   - ✅ Publishes to PyPI with Trusted Publishing
   - ✅ Creates GitHub Release with your PR description
   - ✅ Attaches build artifacts to release

**That's it!** The package is now live on PyPI.

### Versioning Guidelines

We follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

- **MAJOR** (`1.0.0` → `2.0.0`): Breaking changes, incompatible API changes
- **MINOR** (`0.5.0` → `0.6.0`): New features, backward compatible
- **PATCH** (`0.5.5` → `0.5.6`): Bug fixes, no new features

### Pre-releases (Optional)

For testing releases before production:

- Alpha: `0.6.0a1`
- Beta: `0.6.0b1`
- Release Candidate: `0.6.0rc1`

### Troubleshooting Releases

**If tag already exists:**
```bash
# Delete local and remote tag if needed
git tag -d v0.5.7
git push origin :refs/tags/v0.5.7
```

**If PyPI publish fails:**
- Check workflow logs in GitHub Actions
- Verify PyPI Trusted Publishing is configured
- Ensure version doesn't already exist on PyPI (versions can't be re-uploaded)

**If release was incorrect:**
- PyPI packages cannot be deleted (policy)
- You must publish a new patch version
- Use "yank" feature on PyPI if critically broken

## Testing Locally Before Release

1. **Build the package**:
   ```bash
   uv build
   ```

2. **Install locally**:
   ```bash
   pip install dist/*.whl
   ```

3. **Test the installed package**:
   ```bash
   gsb --version
   gsb --help
   ```

## Code Style

- Use type annotations for all functions
- Write docstrings in Google style
- Keep functions focused and single-purpose
- Follow existing patterns in the codebase

## Questions?

Open an issue or start a discussion on GitHub!
