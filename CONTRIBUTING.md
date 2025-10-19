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

### Branch Protection & CI Requirements

The `main` branch is protected with required status checks. **All PRs must pass CI before merging:**

**Required Checks:**
- ✅ Test on Python 3.12
- ✅ Test on Python 3.13
- ✅ Type checking with mypy
- ✅ Build package

**What This Means:**
- You cannot merge a PR until all 4 checks pass
- PRs must be up to date with `main` before merging
- Failed tests will block the merge button
- This ensures all releases are based on tested, working code

**CI runs automatically** when you:
- Push commits to a branch
- Open or update a pull request
- CI typically completes in ~30 seconds

If CI fails, check the workflow logs in GitHub Actions to see which tests failed and why.

## Release Process

Releases are automated through GitHub Actions. Only maintainers can create releases.

### For Maintainers: Creating a Release

**Important:** Bump the version using `uv version --bump` before creating your release PR.

1. **Create a feature branch** with your changes:
   ```bash
   git checkout -b feature/add-feature-x
   # or
   git checkout -b fix/bug-y
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "Add feature X"
   ```

3. **Bump the version** based on your changes:
   ```bash
   # For stable releases (publishes to Production PyPI):
   uv version --bump major      # Breaking changes (1.2.3 → 2.0.0)
   uv version --bump minor      # New features (1.2.3 → 1.3.0)
   uv version --bump patch      # Bug fixes (1.2.3 → 1.2.4)

   # For pre-releases (publishes to TestPyPI):
   uv version --bump minor --bump rc     # Release candidate (0.5.6 → 0.6.0rc1)
   uv version --bump patch --bump beta   # Beta (0.5.6 → 0.5.7b1)
   uv version --bump major --bump alpha  # Alpha (0.5.6 → 1.0.0a1)
   uv version --bump patch --bump dev    # Development (0.5.6 → 0.5.7.dev1)
   ```

4. **Commit the version bump:**
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "chore: bump version to $(uv version --short)"
   ```

5. **Write a comprehensive PR description** (becomes release notes):
   ```markdown
   Title: Add feature X / Fix bug Y

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

6. **Create the pull request** on GitHub

7. **Add `release` label** to the PR
   - This is the only required label
   - The workflow automatically detects PyPI target from version string (rc/alpha/beta/dev → TestPyPI, otherwise → PyPI)

8. **Get approval and merge**
   - CI will run all tests
   - Once approved, merge the PR

9. **Automated publishing** (happens automatically after merge):
   - ✅ Extracts version from `pyproject.toml`
   - ✅ Determines target from version (rc/alpha/beta/dev → TestPyPI, else → PyPI)
   - ✅ Creates Git tag (e.g., `v0.6.0`)
   - ✅ Builds wheel and source distribution
   - ✅ Publishes to appropriate PyPI
   - ✅ Creates GitHub Release with your PR description
   - ✅ Attaches build artifacts to release

**That's it!** The package is automatically published to the correct PyPI based on version string.

### If You Forgot to Bump the Version

If you merged without bumping the version, the workflow will fail with a "tag already exists" error. To fix:

```bash
# Bump version on main
git checkout main
git pull
uv version --bump patch  # or minor, major, etc.
git commit -am "chore: bump version to $(uv version --short)"
git push

# Go to GitHub Actions and click "Re-run failed jobs"
```

### Installing from TestPyPI

To install the test release:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gs-batch-pdf==0.5.7
```

The `--extra-index-url` is needed because dependencies are not on TestPyPI.

### Versioning Guidelines

We follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

**Standard Releases:**
- **MAJOR** (`1.0.0` → `2.0.0`): Breaking changes, incompatible API changes
  - Command: `uv version --bump major`
- **MINOR** (`0.5.0` → `0.6.0`): New features, backward compatible
  - Command: `uv version --bump minor`
- **PATCH** (`0.5.5` → `0.5.6`): Bug fixes, no new features
  - Command: `uv version --bump patch`

**Pre-releases (for testing before production):**
- **Alpha** (`0.6.0a1`): Early testing version
  - Command: `uv version --bump minor --bump alpha` (or `patch`/`major` + `alpha`)
- **Beta** (`0.6.0b1`): Feature-complete, testing for bugs
  - Command: `uv version --bump minor --bump beta` (or `patch`/`major` + `beta`)
- **Release Candidate** (`0.6.0rc1`): Final testing before release
  - Command: `uv version --bump minor --bump rc` (or `patch`/`major` + `rc`)
- **Dev release** (`0.5.7.dev1`): Development snapshots
  - Command: `uv version --bump patch --bump dev` (or `minor`/`major` + `dev`)

**Version bumping examples:**
```bash
# Standard releases
uv version --bump patch    # 0.5.6 → 0.5.7
uv version --bump minor    # 0.5.7 → 0.6.0
uv version --bump major    # 0.6.0 → 1.0.0

# Pre-releases
uv version --bump minor --bump rc     # 0.5.6 → 0.6.0rc1
uv version --bump patch --bump beta   # 0.5.6 → 0.5.7b1
uv version --bump major --bump alpha  # 0.5.6 → 1.0.0a1
```

### Automatic Target Selection

**The workflow automatically determines where to publish based on version string:**

**Production PyPI (https://pypi.org):**
- Version does not contain: `rc`, `alpha`, `beta`, `dev`, `a[0-9]`, `b[0-9]`
- Examples: `0.5.7`, `0.6.0`, `1.0.0`, `0.5.7.post1`
- Users install with: `pip install gs-batch-pdf`

**TestPyPI (https://test.pypi.org):**
- Version contains pre-release identifiers: `rc`, `alpha`, `beta`, `dev`, `a[0-9]`, `b[0-9]`
- Examples: `0.6.0rc1`, `0.5.7b1`, `1.0.0a1`, `0.5.7.dev1`
- Users install with: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gs-batch-pdf`

**Benefits:**
- ✅ Impossible to accidentally publish pre-releases to production
- ✅ Clear separation between testing and production
- ✅ Version string directly implies target

### Troubleshooting Releases

**If tag already exists:**
The workflow will fail with a clear error. See "If You Forgot to Bump the Version" section above.

**If PyPI publish fails:**
- Check workflow logs in GitHub Actions
- Verify PyPI Trusted Publishing is configured for the repository
- Ensure version doesn't already exist on PyPI (versions can't be re-uploaded)

**If release was incorrect:**
- PyPI packages cannot be deleted (policy)
- You must publish a new patch version (use `bump:patch`)
- Use "yank" feature on PyPI if critically broken
- For TestPyPI, you can delete and retry

**Common mistakes:**
- Forgetting to add `bump:X` label → Workflow fails with error
- Adding only `bump:rc` without version component → Workflow fails (pre-releases need TWO labels)
- Manually editing version in PR → Version gets bumped twice (don't do this!)
- Not writing PR description → Release notes will be empty

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
