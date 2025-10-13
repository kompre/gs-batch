# Task: CI/CD Workflows - Build, Test, and PyPI Publishing

**Original Objective:** Set up GitHub workflows to build, test, and publish to PyPI with version management ensuring main branch reflects published package state

**Status:** Proposal - Awaiting User Approval

---

## Problem Analysis

### Current State
- No CI/CD workflows configured
- Manual building and publishing to PyPI
- No automated testing on PRs
- No guarantee that main branch reflects PyPI state
- Version management is manual

### Requirements
1. Automated testing on all changes
2. Automated PyPI publishing
3. Version synchronization between Git tags and PyPI
4. Security best practices (no API tokens)
5. Clear release process

---

## Strategy: Label-Triggered Release Workflow

### Core Principle
**PR label "release" triggers automated release on merge**

When you merge a PR labeled "release":
1. Workflow reads version from pyproject.toml
2. Creates Git tag matching that version (e.g., `v0.5.6`)
3. Builds the package
4. Publishes to PyPI
5. Creates GitHub Release with PR description as changelog

This ensures **main branch state = PyPI published version** after merge, with **zero manual steps**.

### Why This Approach?

**Pros:**
- ✅ Fully automated (no manual tagging needed)
- ✅ Zero risk of version/tag mismatch (reads from pyproject.toml)
- ✅ PR description becomes release notes (built-in changelog)
- ✅ Clear audit trail (label + PR + tag + release)
- ✅ One decision point: "Is this PR a release?" → Add label
- ✅ Works with existing workflow (manual version bumps in PRs)
- ✅ Can't forget to tag or typo the version

**Cons:**
- Release happens immediately on merge (can't delay)
- Requires good PR descriptions for meaningful release notes
- Need to remember to add "release" label before merging

---

## Implementation Plan

### Phase 1: Continuous Integration Workflow

**File:** `.github/workflows/ci.yml`

**Triggers:**
- Every push to any branch
- All pull requests

**Jobs:**

1. **Test Matrix**
   - Python versions: 3.12, 3.13
   - OS: ubuntu-latest (Linux)
   - Install Ghostscript
   - Run `uv sync`
   - Execute `uv run pytest`
   - Upload coverage reports

2. **Type Checking**
   - Run `uv run mypy gs_batch/`
   - Verify type annotations

3. **Build Verification**
   - Run `uv build`
   - Verify package builds successfully
   - Check wheel and sdist created

**Benefits:**
- Fast feedback on PRs
- Catch issues before merge
- Verify buildability

---

### Phase 2: Label-Triggered Release Workflow

**File:** `.github/workflows/release.yml`

**Trigger:**
- Merged pull requests with label "release"

**Trigger Configuration:**
```yaml
on:
  pull_request:
    types: [closed]

jobs:
  release:
    if: github.event.pull_request.merged == true && contains(github.event.pull_request.labels.*.name, 'release')
```

**Important:** The workflow only runs when:
1. PR is closed AND
2. PR was merged (not just closed) AND
3. PR has the "release" label

**Security: Trusted Publishing (OpenID Connect)**
- No API tokens stored
- GitHub authenticates directly with PyPI
- Token generated per-publish, expires immediately
- Requires one-time PyPI configuration

**Jobs:**

1. **Extract Version from pyproject.toml**
   - Parse version from `pyproject.toml`
   - Example: `0.5.6`
   - Create tag name: `v0.5.6`
   - Check if tag already exists (fail if yes)

2. **Create and Push Git Tag**
   - Create annotated tag with version
   - Push tag to repository
   - This becomes the release identifier

3. **Build Package**
   - Set up Python 3.12
   - Install `uv`
   - Run `uv build`
   - Creates wheel (.whl) and source dist (.tar.gz)
   - Store artifacts

4. **Publish to PyPI**
   - Use official action: `pypa/gh-action-pypi-publish@release/v1`
   - Publishes with Trusted Publishing (OIDC)
   - Generates digital attestations (Sigstore)
   - Atomic upload (all files together)

5. **Create GitHub Release**
   - Create release from the created tag
   - Include **PR title and description** as release notes
   - Auto-generate changelog from commits since last release
   - Attach build artifacts (wheel + sdist)
   - Mark as latest release

**Workflow Example:**
```bash
# 1. Create PR with version bump to 0.5.6 in pyproject.toml
# 2. Write good PR description (it becomes release notes!)
# 3. Add "release" label to the PR
# 4. Get approval and merge
# 5. Workflow automatically:
#    - Reads version (0.5.6)
#    - Creates tag (v0.5.6)
#    - Publishes to PyPI
#    - Creates GitHub Release with your PR description
```

---

### Phase 3: Version Guard Workflow (Optional)

**File:** `.github/workflows/version-check.yml`

**Trigger:**
- Pull requests targeting `main` branch

**Purpose:**
Prevent merging PRs without version bump

**Jobs:**

1. **Check Version Increased**
   - Compare version in PR vs main
   - Fail if version not increased
   - Optional: Allow bypass with label `skip-version-check`

**Benefits:**
- Enforces version bumps
- Prevents forgotten version updates
- Maintains discipline

**Drawbacks:**
- May be too strict for documentation-only PRs
- Requires version bump even for minor fixes

**Recommendation:** Start without this, add later if needed

---

## PyPI Trusted Publishing Setup

### One-Time Configuration

1. **On PyPI:**
   - Go to Account Settings → Publishing
   - Add new publisher
   - Select GitHub
   - Repository: `kompre/gs-batch`
   - Workflow: `release.yml`
   - Environment: leave blank (or use `release`)

2. **No GitHub Configuration Needed**
   - Workflow automatically uses OIDC
   - Permissions configured in workflow file

### Security Benefits
- ✅ No long-lived API tokens
- ✅ No secrets in GitHub
- ✅ Automatic token rotation
- ✅ Audit trail via GitHub logs
- ✅ Digital attestations for packages

---

## Release Process

### Standard Release Flow with Label Trigger

1. **Development**
   ```bash
   # Make changes in feature branch
   git checkout -b feature/new-feature
   # Make commits
   ```

2. **Update Version in PR**
   ```toml
   # pyproject.toml
   [project]
   version = "0.5.6"  # Increment from 0.5.5
   ```

3. **Create PR with Good Description**
   ```markdown
   Title: Release v0.5.6: Add CI/CD workflows

   ## Summary
   Adds GitHub Actions workflows for automated testing and publishing.

   ## Changes
   - Add CI workflow for testing
   - Add release workflow with Trusted Publishing
   - Add automated tagging on merge

   ## Breaking Changes
   None
   ```

   **This description becomes your release notes!**

4. **Add "release" Label to PR**
   - In GitHub PR interface
   - Add label: `release`
   - This marks it for automatic release on merge

5. **Review and Merge**
   - CI runs tests
   - Code review and approval
   - **Merge to main**

6. **Automatic Publishing (Zero Manual Steps!)**
   - Workflow detects "release" label on merged PR
   - Reads version from pyproject.toml (`0.5.6`)
   - Creates Git tag (`v0.5.6`)
   - Builds package
   - Publishes to PyPI
   - Creates GitHub Release with your PR description

   **Done! Package is live on PyPI.**

### Versioning Guidelines

**Semantic Versioning (SemVer):**
- `MAJOR.MINOR.PATCH`
- `1.0.0` format

**When to Bump:**
- **MAJOR (1.0.0 → 2.0.0):** Breaking changes, incompatible API
- **MINOR (0.5.0 → 0.6.0):** New features, backward compatible
- **PATCH (0.5.5 → 0.5.6):** Bug fixes, no new features

**Pre-releases (Optional):**
- `0.6.0a1` - Alpha
- `0.6.0b1` - Beta
- `0.6.0rc1` - Release candidate

---

## Implementation Steps

### Step 1: Create CI Workflow

**File:** `.github/workflows/ci.yml`

Features:
- Test matrix (Python 3.12, 3.13)
- Install Ghostscript
- Run pytest with coverage
- Type checking with mypy
- Build verification

### Step 2: Configure PyPI Trusted Publishing

**On PyPI:**
1. Log in to pypi.org
2. Go to "Publishing" settings
3. Add GitHub as trusted publisher
4. Configure: `kompre/gs-batch`, workflow `release.yml`

### Step 3: Create Release Workflow

**File:** `.github/workflows/release.yml`

Features:
- Tag validation (matches pyproject.toml)
- Build wheel + sdist
- Publish with Trusted Publishing
- Create GitHub Release
- Upload artifacts

### Step 4: Documentation

**Update:** `README.md` or create `CONTRIBUTING.md`

Document:
- Release process
- Version bump guidelines
- Tag creation
- Testing locally before release

### Step 5: Test Release

**Recommendation:** Use TestPyPI first

Modify workflow to publish to TestPyPI:
```yaml
with:
  repository-url: https://test.pypi.org/legacy/
```

Test full cycle, then switch to production PyPI.

---

## Additional Considerations

### Build Tool: UV

The project uses `uv` for dependency management. Workflows will use:
```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Sync dependencies
  run: uv sync

- name: Run tests
  run: uv run pytest
```

### Caching

Enable caching for faster workflows:
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

### Ghostscript Dependency

Tests require Ghostscript. Install in CI:
```yaml
- name: Install Ghostscript
  run: sudo apt-get install -y ghostscript
```

### Test Assets

Ensure test PDFs are committed to repo:
- `tests/assets/originals/*.pdf`

### Versioning in Code

Current implementation:
```python
from importlib.metadata import version
def get_version() -> str:
    try:
        return version("gs-batch-pdf")
    except PackageNotFoundError:
        return "unknown"
```

This works perfectly - reads from installed package metadata.

---

## Alternative Approaches Considered

### 1. Automatic Semantic Versioning

**Tool:** python-semantic-release

**How it works:**
- Parses commit messages (Conventional Commits)
- Auto-bumps version based on commits
- `fix:` → patch, `feat:` → minor, `BREAKING CHANGE:` → major

**Pros:**
- Fully automated
- No manual version bumps

**Cons:**
- Requires strict commit message discipline
- Less control over releases
- Overkill for small projects
- Learning curve for contributors

**Decision:** Not recommended for this project. Manual control is better.

### 2. Version from Git Tags

**How it works:**
- Use `setuptools-scm` or similar
- Version derived from Git tags
- No version in pyproject.toml

**Pros:**
- Single source of truth (Git tags)
- No manual version updates

**Cons:**
- Complex setup
- Less transparent
- Harder to debug
- Non-standard approach

**Decision:** Keep version in pyproject.toml (current approach).

### 3. Publish on Every Main Push

**How it works:**
- Every merge to main publishes to PyPI
- Auto-increment version

**Pros:**
- Maximum automation

**Cons:**
- No control over release timing
- Can't batch fixes
- May publish broken versions
- Not recommended practice

**Decision:** Use tag-based releases for control.

---

## Success Criteria

After implementation:

1. ✅ CI runs on all PRs and pushes
2. ✅ Tests execute on Python 3.12 and 3.13
3. ✅ Type checking passes
4. ✅ Package builds successfully
5. ✅ Pushing version tag publishes to PyPI
6. ✅ GitHub Release created automatically
7. ✅ No API tokens stored in GitHub
8. ✅ Main branch state matches PyPI after tag
9. ✅ Process documented for contributors

---

## Rollback Plan

If publishing fails:

1. **GitHub Release:** Can be deleted manually
2. **PyPI Package:** Cannot be deleted (PyPI policy)
   - Must publish new patch version
   - Mark as yanked if critical issue
3. **Git Tag:** Can be deleted and recreated
   ```bash
   git tag -d v0.5.6
   git push origin :refs/tags/v0.5.6
   ```

**Prevention:**
- Always test builds locally first
- Use TestPyPI for validation
- Review changes carefully before tagging

---

## Timeline

**Total Estimated Time:** 2-3 hours

- Phase 1 (CI): 1 hour
  - Create workflow file
  - Test on actual PR
  - Adjust for Ghostscript setup

- Phase 2 (Release): 1-1.5 hours
  - PyPI Trusted Publishing setup
  - Create workflow file
  - Test with TestPyPI
  - Do actual release

- Phase 3 (Documentation): 30 minutes
  - Update README or CONTRIBUTING.md
  - Document release process

---

## Questions to Address

1. **Should we add version-check workflow?**
   - Recommendation: Start without, add if needed

2. **Test on Windows/macOS in CI?**
   - Current: Linux only
   - Recommendation: Add later if issues arise

3. **Code coverage requirements?**
   - Current: No enforcement
   - Recommendation: Track but don't block

4. **Branch protection rules?**
   - Require CI to pass before merge
   - Recommendation: Yes, add after CI works

---

## Next Steps

1. Review and approve this proposal
2. Create CI workflow (`ci.yml`)
3. Test CI on a PR
4. Configure PyPI Trusted Publishing
5. Create release workflow (`release.yml`)
6. Test release with TestPyPI
7. Document process
8. Do first automated release

---

**Ready to proceed?**
