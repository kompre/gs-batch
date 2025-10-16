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

Releases are automated through GitHub Actions using label-triggered version bumping. Only maintainers can create releases.

### For Maintainers: Creating a Release

**Important:** You do NOT need to manually edit version numbers! The workflow automatically bumps the version using `uv version --bump`.

1. **Create a release PR** with your changes:
   ```bash
   git checkout -b release/add-feature-x
   # or
   git checkout -b release/fix-bug-y
   ```

2. **Make your changes and commit** (NO version editing needed!)
   ```bash
   git add .
   git commit -m "Add feature X"
   # Note: Do NOT edit pyproject.toml version
   ```

3. **Write a comprehensive PR description** (becomes release notes):
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

4. **Create the pull request** on GitHub

5. **Add release labels** to the PR (REQUIRED):

   **Required labels:**
   - `release` - Triggers the release workflow
   - **One bump type label** (choose based on changes):
     - **Production PyPI (stable releases):**
       - `bump:major` - Breaking changes (1.2.3 → 2.0.0)
       - `bump:minor` - New features, backward compatible (1.2.3 → 1.3.0)
       - `bump:patch` - Bug fixes only (1.2.3 → 1.2.4)
       - `bump:stable` - Remove pre-release suffix (1.2.4rc1 → 1.2.4)
     - **TestPyPI (pre-releases for testing):**
       - `bump:alpha` - Alpha pre-release (1.2.3 → 1.2.4a1)
       - `bump:beta` - Beta pre-release (1.2.3 → 1.2.4b1)
       - `bump:rc` - Release candidate (1.2.3 → 1.2.4rc1)
       - `bump:post` - Post-release (1.2.4 → 1.2.4.post1)
       - `bump:dev` - Development (1.2.3 → 1.2.4.dev1)

   **Example:** For a new feature release, add labels: `release`, `bump:minor` (automatically publishes to production PyPI)

6. **Get approval and merge**
   - CI will run all tests
   - Once approved, merge the PR

7. **Automated publishing** (happens automatically after merge):
   - ✅ Workflow extracts bump type from labels
   - ✅ Automatically determines target (PyPI or TestPyPI) based on bump type
   - ✅ Runs `uv version --bump <type>` to update `pyproject.toml`
   - ✅ Commits version change to main with `[skip ci]`
   - ✅ Creates Git tag (e.g., `v0.5.7`)
   - ✅ Builds wheel and source distribution
   - ✅ Publishes to correct PyPI (production for stable, TestPyPI for pre-releases)
   - ✅ Creates GitHub Release with your PR description
   - ✅ Attaches build artifacts to release

**That's it!** The version is automatically bumped and published to the correct PyPI based on bump type.

> **Note:** After merge, main branch will have one additional commit containing the version bump.

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
  - Use label: `bump:major`
- **MINOR** (`0.5.0` → `0.6.0`): New features, backward compatible
  - Use label: `bump:minor`
- **PATCH** (`0.5.5` → `0.5.6`): Bug fixes, no new features
  - Use label: `bump:patch`

**Pre-releases (for testing before production):**
- **Alpha** (`0.6.0a1`): Early testing version
  - Use label: `bump:alpha`
- **Beta** (`0.6.0b1`): Feature-complete, testing for bugs
  - Use label: `bump:beta`
- **Release Candidate** (`0.6.0rc1`): Final testing before release
  - Use label: `bump:rc`
- **Stabilize** (`0.6.0rc1` → `0.6.0`): Remove pre-release suffix
  - Use label: `bump:stable`

**Special cases:**
- **Post-release** (`0.5.6.post1`): Documentation or packaging fixes
  - Use label: `bump:post`
- **Dev release** (`0.5.7.dev1`): Development snapshots
  - Use label: `bump:dev`

### How Version Bumping Works

The workflow uses `uv version --bump <type>` which automatically:
- Reads the current version from `pyproject.toml`
- Calculates the next version based on bump type
- Updates `pyproject.toml` with the new version
- Commits the change to main branch

**Examples:**
- Current: `0.5.6rc2` + `bump:stable` → `0.5.7`
- Current: `0.5.7` + `bump:patch` → `0.5.8`
- Current: `0.5.7` + `bump:minor` → `0.6.0`
- Current: `0.5.7` + `bump:rc` → `0.5.8rc1`

### Automatic Target Selection

**The workflow automatically determines where to publish based on your bump type label:**

**Production PyPI (https://pypi.org):**
- `bump:major`, `bump:minor`, `bump:patch`, `bump:stable`
- These are stable releases meant for production use
- Users install with: `pip install gs-batch-pdf`

**TestPyPI (https://test.pypi.org):**
- `bump:alpha`, `bump:beta`, `bump:rc`, `bump:post`, `bump:dev`
- These are pre-releases for testing only
- Users install with: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gs-batch-pdf`

**Benefits of this policy:**
- ✅ Impossible to accidentally publish pre-releases to production
- ✅ No need for manual target selection
- ✅ Clear separation between testing and production
- ✅ Bump type directly implies stability level

### Troubleshooting Releases

**If workflow fails due to missing bump label:**
- Error message will list required labels
- Add the appropriate `bump:X` label to your PR
- The workflow only runs on merge, so you may need to close and reopen the PR to trigger it again

**If tag already exists:**
The workflow will fail with a clear error. To fix:
```bash
# Delete local and remote tag if needed
git tag -d v0.5.7
git push origin :refs/tags/v0.5.7
# Then trigger workflow again or manually create a new release
```

**If branch protection blocks version commit:**
- Configure branch protection to allow `github-actions[bot]` to push
- Or adjust protection rules to only apply to PRs, not direct pushes from workflows
- Check GitHub Actions logs for permission errors

**If PyPI publish fails:**
- Check workflow logs in GitHub Actions
- Verify PyPI Trusted Publishing is configured
- Ensure version doesn't already exist on PyPI (versions can't be re-uploaded)
- Check that bump type label was correctly applied

**If release was incorrect:**
- PyPI packages cannot be deleted (policy)
- You must publish a new patch version (use `bump:patch`)
- Use "yank" feature on PyPI if critically broken
- For TestPyPI, you can delete and retry

**Common mistakes:**
- Forgetting to add `bump:X` label → Workflow fails with error
- Adding multiple bump labels → Workflow uses first found
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
