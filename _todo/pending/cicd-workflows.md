# Task: CI/CD Workflows - Build, Test, and PyPI Publishing

**Original Objective:** Set up GitHub workflows to build, test, and publish to PyPI with version management ensuring main branch reflects published package state

**Status:** In Progress - Phase 1 Complete

---

## Session Activity Log

### 2025-10-15: Phase 1 Implementation & Ghostscript Fix

#### Work Completed

**Phase 1: CI Workflow Implementation**
- ✅ Created `.github/workflows/ci.yml`
- ✅ Configured test matrix (Python 3.12, 3.13)
- ✅ Added type checking job (mypy)
- ✅ Added build verification job
- ✅ All tests passing successfully

**Critical Issue Fixed: Ghostscript CI Failures**

*Problem Discovered:*
- Initial CI runs failed with "FILE NOT PROCESSED!" errors
- Snap-installed Ghostscript couldn't access temporary files
- Sandboxing restrictions prevented file operations in `/tmp`

*Root Causes:*
1. Snap confinement blocked access to pytest's temporary directories
2. No health check in CLI to detect misconfigured Ghostscript
3. Silent failures with unhelpful error messages

*Solutions Implemented:*

1. **CI Workflow Fix** ([.github/workflows/ci.yml](../.github/workflows/ci.yml:30-38))
   - Replaced snap installation with apt-get
   - Simplified: `sudo apt-get install -y ghostscript`
   - Removed complex download/extraction steps
   - No PATH manipulation needed
   - apt version has no sandboxing issues

2. **CLI Health Check** ([gs_batch/gs_batch.py](../gs_batch/gs_batch.py:431-501))
   - Added `check_ghostscript_available()` function
   - Runs at startup before processing files
   - Two-stage verification:
     * Command exists and responds to `--version`
     * Actual execution test (catches sandboxing)
   - Provides helpful error messages with troubleshooting
   - Detects snap issues and suggests apt alternative
   - Early exit with clear guidance

*Results:*
- ✅ All 10 tests passing on Python 3.12 and 3.13
- ✅ CI runtime: ~58 seconds per test job
- ✅ Files properly processed (no more "FILE NOT PROCESSED!")
- ✅ Better user experience with immediate feedback

*Commits:*
- `f399c07` - Fix test assertion for PDF size variations
- `d49aaf8` - Check Ghostscript return codes to detect failures
- `53aeb82` - Use Ghostscript 10.04.0 for CI testing
- `3a7362a` - Fix Ghostscript PATH issue in CI tests
- `824a994` - Fix CI Ghostscript installation and add health check

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

## Phase 2: Next Steps - Release Workflow

### Current State
- ✅ Phase 1 Complete: CI workflow working perfectly
- ✅ Tests passing on Python 3.12 and 3.13
- ✅ Type checking and build verification working
- ✅ Ghostscript health check implemented

### Remaining Work

#### 2.1 PyPI Trusted Publishing Setup (User Action Required)

**On PyPI (pypi.org):**
1. Log in to your PyPI account
2. Navigate to Account Settings → Publishing
3. Add new trusted publisher:
   - Publisher: GitHub
   - Owner: `kompre`
   - Repository name: `gs-batch`
   - Workflow filename: `release.yml`
   - Environment name: (leave blank or use `release`)

This is a **one-time setup** that enables secure publishing without API tokens.

#### 2.2 Create Release Workflow

**File to create:** `.github/workflows/release.yml`

**Workflow will:**
1. Trigger on merged PRs with "release" label
2. Extract version from `pyproject.toml`
3. Create Git tag (e.g., `v0.5.6`)
4. Build package with `uv build`
5. Publish to PyPI using Trusted Publishing (OIDC)
6. Create GitHub Release with PR description as changelog
7. Attach build artifacts to release

**Key Features:**
- Label-triggered (add "release" label to PR before merging)
- Zero manual steps after merge
- PR description becomes release notes
- Automatic tag creation from version
- Digital attestations via Sigstore

#### 2.3 Create CONTRIBUTING.md

Document the release process:
- How to bump version in `pyproject.toml`
- How to write good PR descriptions (they become release notes!)
- How to add "release" label
- Versioning guidelines (SemVer)
- Troubleshooting section

#### 2.4 Test Release Flow

**Recommendation: Test with TestPyPI first**

1. Modify `release.yml` to use TestPyPI:
   ```yaml
   repository-url: https://test.pypi.org/legacy/
   ```
2. Create test PR with version bump
3. Add "release" label
4. Merge and verify workflow
5. Check package on test.pypi.org
6. Switch to production PyPI

#### 2.5 First Production Release

Once tested:
1. Create PR with real version bump
2. Write comprehensive PR description
3. Add "release" label
4. Merge to main
5. Monitor workflow execution
6. Verify package on PyPI
7. Test installation: `pip install gs-batch-pdf`

### Estimated Time
- PyPI setup: 10 minutes
- Release workflow creation: 1 hour
- Documentation: 30 minutes
- Testing (TestPyPI): 30 minutes
- First release: 30 minutes

**Total: ~2.5 hours**

### User Decisions

1. **PyPI/TestPyPI Setup:** ✅ TestPyPI configured and ready
2. **Test approach:** ✅ Test with TestPyPI first
3. **Branch protection rules:** ✅ Yes, enable after testing
4. **Version-check workflow:** ✅ Yes, implement it (Phase 3)

### Implementation Order

**Phase 2A: Release Workflow (TestPyPI)**
1. Create `.github/workflows/release.yml` targeting TestPyPI
2. Create `CONTRIBUTING.md` with release process documentation
3. Test release flow with version bump PR
4. Verify on test.pypi.org

**Phase 2B: Version Check Workflow**
1. Create `.github/workflows/version-check.yml`
2. Enforce version bumps on PRs to main
3. Allow bypass with `skip-version-check` label
4. Test with dummy PR

**Phase 2C: Production Release**
1. Switch release workflow from TestPyPI to production PyPI
2. Configure production PyPI Trusted Publishing
3. Enable branch protection rules
4. First production release

---

### 2025-10-15: Phase 2 Implementation - Release Workflows

#### Phase 2A: Release Workflow (TestPyPI) - ✅ Complete

**Files Created/Modified:**
1. **`.github/workflows/release.yml`** - Release automation
   - Configured to publish to TestPyPI
   - Label-triggered on merged PRs with "release" label
   - Extracts version from pyproject.toml
   - Creates Git tags automatically
   - Builds package with `uv build`
   - Publishes with Trusted Publishing (OIDC)
   - Creates GitHub Release with PR description
   - Attaches build artifacts

2. **`.github/workflows/version-check.yml`** - Version enforcement
   - Runs on all PRs to main
   - Compares PR version vs main version
   - Fails if version not bumped
   - Validates SemVer format
   - Allows bypass with `skip-version-check` label
   - Posts helpful comment on failure

3. **`CONTRIBUTING.md`** - Updated documentation
   - Added TestPyPI installation instructions
   - Documented release process step-by-step
   - Included versioning guidelines
   - Added troubleshooting section

**Current Status:**
- ✅ Release workflow targeting TestPyPI
- ✅ Version-check workflow enforcing version bumps
- ✅ Documentation updated
- ✅ All committed and pushed

**Next Steps:**
1. Test the release process with a version bump PR
2. Verify TestPyPI publishing works
3. Switch to production PyPI once validated
4. Enable branch protection rules

**Current Version:** 0.5.5
**Test Version Target:** 0.5.6

---

### 2025-10-15 (Later): Phase 2 Redesign - Automated Version Bumping

#### Major Strategy Change

**Previous Approach (Discarded):**
- User manually bumps version in PR
- Workflow reads version from pyproject.toml
- Creates tag and publishes

**New Approach (Implemented):**
- NO manual version editing required
- Version bump happens automatically via `uv version --bump <type>`
- Bump type determined by PR labels
- Version committed to main after merge

#### Motivation for Change
User requested automated version bumping using uv's built-in capabilities:
- Eliminates manual version editing errors
- Leverages uv's semantic versioning support
- Clearer release intent via labels
- Follows modern Python tooling best practices

#### Files Modified

**1. Deleted `.github/workflows/version-check.yml`**
- No longer needed (PRs don't contain version bumps)
- Version checking would always fail with new approach
- Version bumping happens post-merge

**2. Completely Redesigned `.github/workflows/release.yml`**

New workflow features:
- **Label extraction**: Parses `bump:X` label from PR
- **Bump type validation**: Ensures label matches uv's supported values
- **Automatic target selection**: PyPI for stable (major/minor/patch/stable), TestPyPI for pre-releases (alpha/beta/rc/dev/post)
- **Automated version bump**: Runs `uv version --bump <type>`
- **Version commit**: Commits updated pyproject.toml to main with `[skip ci]`
- **Concurrency control**: Queues releases instead of running parallel
- **Smart pre-release detection**: Auto-marks GitHub releases as pre-release for alpha/beta/rc

Supported bump types (from `uv version --bump`):
- **major**: 1.2.3 → 2.0.0 (breaking changes)
- **minor**: 1.2.3 → 1.3.0 (new features)
- **patch**: 1.2.3 → 1.2.4 (bug fixes)
- **alpha**: 1.2.3 → 1.2.4a1 (alpha pre-release)
- **beta**: 1.2.3 → 1.2.4b1 (beta pre-release)
- **rc**: 1.2.3 → 1.2.4rc1 (release candidate)
- **stable**: 1.2.4rc1 → 1.2.4 (remove pre-release suffix)
- **post**: 1.2.3 → 1.2.3.post1 (post-release)
- **dev**: 1.2.3 → 1.2.4.dev1 (development release)

Workflow steps:
1. Checkout main after merge
2. Extract and validate bump type from `bump:X` label
3. Automatically determine target (PyPI vs TestPyPI) based on bump type
4. Run `uv version --bump <type>` to update pyproject.toml
5. Commit version change to main (includes PR co-author)
6. Check tag doesn't already exist
7. Create annotated tag with metadata
8. Build package
9. Publish to correct PyPI (automatic selection)
10. Create GitHub Release (marks as pre-release if needed)

**3. Ready to Update `CONTRIBUTING.md`**
- Will document new label-based release process
- Remove references to manual version editing
- Add examples for different release types

#### Branch Protection Considerations

**Challenge:** Workflow needs to push version commit to protected main branch.

**Solutions investigated:**
1. **GitHub App token** (most secure, requires setup)
2. **Admin PAT** (simpler, less secure)
3. **Relaxed protection** (require CI on PRs, allow workflow pushes)

**Current implementation:** Using default `GITHUB_TOKEN`
- Works if branch protection allows Actions bot
- May need configuration based on branch protection rules
- Can upgrade to GitHub App if needed

**Recommendation:**
- Start with current implementation
- Configure branch protection to allow `github-actions[bot]`
- Or adjust branch protection to only enforce rules on PRs, not direct pushes from workflows

#### Concurrency Control

Added concurrency group to prevent race conditions:
```yaml
concurrency:
  group: release
  cancel-in-progress: false  # Queue instead of cancel
```

If multiple release PRs merge quickly, releases queue instead of conflicting.

#### New Release Process

**For developers:**
1. Create PR with changes (NO version editing!)
2. Add labels:
   - `release` (required)
   - `bump:minor` or other bump type (required - automatically determines target)
3. Get CI to pass, obtain approval
4. Merge PR
5. Workflow handles everything: bump → commit → tag → build → publish to correct PyPI

**After merge:**
- Main branch will have one additional commit (the version bump)
- Commit message includes `[skip ci]` to avoid triggering CI again
- Tag points to the version bump commit
- Published package matches tagged commit exactly

#### Benefits of New Approach

- ✅ No manual version editing (eliminates typos)
- ✅ Consistent version bumping via uv
- ✅ Clear release intent via labels
- ✅ Version bump recorded in git history
- ✅ Automatic pre-release detection
- ✅ Supports all SemVer patterns including pre-releases
- ✅ Zero manual post-merge steps
- ✅ Co-author attribution in version commit

#### Labels to Create

Need to create these labels in GitHub:
1. `release` - Triggers release workflow (already exists ✅)
2. `bump:major` - Breaking changes (→ PyPI)
3. `bump:minor` - New features (→ PyPI)
4. `bump:patch` - Bug fixes (→ PyPI)
5. `bump:stable` - Stabilize pre-release (→ PyPI)
6. `bump:alpha` - Alpha pre-release (→ TestPyPI)
7. `bump:beta` - Beta pre-release (→ TestPyPI)
8. `bump:rc` - Release candidate (→ TestPyPI)
9. `bump:post` - Post-release (→ TestPyPI)
10. `bump:dev` - Development release (→ TestPyPI)

**Note:** No target labels needed! Target is automatically determined by bump type.

#### Current Status

- ✅ version-check.yml deleted
- ✅ release.yml completely redesigned
- ✅ Automated version bumping implemented
- ✅ Label-based workflow complete
- ✅ Concurrency control added
- ✅ Automatic target selection (no manual target labels!)
- ✅ CONTRIBUTING.md updated with automatic target selection
- ✅ cicd-workflows.md updated
- 🔄 Testing with actual PR pending
- 🔄 Label creation pending

#### Next Steps

1. Update CONTRIBUTING.md with new process
2. Create GitHub labels
3. Test with version bump PR (use `bump:stable` to go from 0.5.6rc2 → 0.5.7)
4. Configure branch protection if needed
5. Verify TestPyPI publishing works
6. Switch to production PyPI once validated

#### Technical Notes

**Current version:** 0.5.6rc2 (pre-release)

**Testing strategy:**
- Use `bump:stable` to create 0.5.7 (removes rc suffix)
- Or use `bump:patch` to create 0.5.7
- Test with `target:testpypi` first
- Monitor GitHub Actions logs for any issues
- Verify commit to main succeeds
- Check tag creation
- Confirm TestPyPI package appears

**Potential issues to watch:**
1. Branch protection blocking workflow commits
2. Race conditions with concurrent merges (mitigated by concurrency group)
3. Missing or invalid bump type label (workflow fails with helpful error)
4. Tag already exists (workflow fails with clear message)

---

### 2025-10-15 (Final): Automatic Target Selection

#### Major Improvement: Removed Manual Target Labels

**Previous approach:**
- Required `target:testpypi` or `target:pypi` label
- Risk of human error (publishing pre-release to production)
- Extra label management overhead

**New approach:**
- Target automatically determined by bump type
- **Production PyPI**: `major`, `minor`, `patch`, `stable`
- **TestPyPI**: `alpha`, `beta`, `rc`, `dev`, `post`
- Impossible to accidentally publish pre-releases to production

#### Rationale

User asked: "Could we automate the target then, according to policy?"

This eliminates the most error-prone part of the workflow:
- Pre-releases should never go to production PyPI
- Stable releases should go to production PyPI
- The bump type already indicates stability level
- Why make developers think about it twice?

#### Implementation

**Modified `.github/workflows/release.yml`:**
```yaml
# Automatic target selection based on bump type
if [[ "$BUMP_TYPE" =~ ^(major|minor|patch|stable)$ ]]; then
  # Production PyPI for stable releases
  repository_url=https://upload.pypi.org/legacy/
else
  # TestPyPI for pre-releases
  repository_url=https://test.pypi.org/legacy/
fi
```

**Updated documentation:**
- CONTRIBUTING.md: Removed all target label references
- Added "Automatic Target Selection" section explaining the policy
- Updated examples to show simpler workflow

**Benefits:**
- ✅ Fewer labels (9 instead of 11)
- ✅ Zero risk of publishing pre-release to production
- ✅ Clearer workflow (bump type implies everything)
- ✅ Policy enforcement built into workflow
- ✅ Simpler mental model for contributors

**Test Plan:**
1. Create labels (9 bump types only)
2. Test PR with `bump:stable` → Should auto-select PyPI
3. Future PR with `bump:rc` → Should auto-select TestPyPI

---
