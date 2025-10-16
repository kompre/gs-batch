# PyPI Publishing Setup Agent

This project served as the basis for creating a reusable Claude Code agent for setting up automated PyPI publishing workflows.

## What is it?

A specialized Claude Code agent that automatically sets up a complete CI/CD pipeline for Python projects, including:
- Continuous Integration (automated testing)
- Automated releases to PyPI/TestPyPI
- Branch protection configuration
- Complete documentation

## Where is it?

The agent is installed globally in your Claude Code config:
```
~/.claude/agents/setup-pypi-publishing.md
```

## How to use it

In any Python project, simply tell Claude Code:

```
Set up automated PyPI publishing with CI/CD
```

or

```
@setup-pypi-publishing configure this project
```

## What it does

1. **Analyzes your project**
   - Detects package manager (uv, poetry, pip)
   - Identifies Python versions to test
   - Finds test framework (pytest, unittest)
   - Detects type checker (mypy, pyright)
   - Identifies external dependencies

2. **Creates CI workflow** (`.github/workflows/ci.yml`)
   - Test matrix for multiple Python versions
   - Type checking (if detected)
   - Build verification
   - Optimized with caching (60-70% faster)

3. **Creates release workflow** (`.github/workflows/release.yml`)
   - Label-triggered releases (`release` + `bump:TYPE`)
   - Automatic version bumping
   - Smart target selection (PyPI vs TestPyPI)
   - OIDC Trusted Publishing (no API tokens)
   - Digital attestations (Sigstore)
   - GitHub Release creation

4. **Generates documentation** (`CONTRIBUTING.md`)
   - Development setup
   - Testing instructions
   - Release process
   - Label reference
   - Branch protection explanation

5. **Creates GitHub labels**
   - `release` - triggers workflow
   - `bump:major`, `bump:minor`, `bump:patch` - production bumps
   - `bump:alpha`, `bump:beta`, `bump:rc` - pre-release bumps
   - `bump:stable`, `bump:dev`, `bump:post` - special cases

6. **Provides configuration guides**
   - PyPI Trusted Publishing setup
   - TestPyPI configuration
   - Branch protection rules
   - Testing instructions

## Key Features

### Automatic Version Bumping
No manual editing of `pyproject.toml`! The workflow uses the package manager's built-in version bumping:
- `uv version --bump <type>`
- `poetry version <type>`

### Smart Target Selection
The bump type automatically determines the publish target:
- **Production (PyPI):** major, minor, patch, stable
- **Pre-release (TestPyPI):** alpha, beta, rc, dev, post

### Performance Optimizations
- Package manager caching (uv, poetry, pip)
- APT package caching for system dependencies
- Parallel job execution
- **Result:** 60-70% faster CI than naive approach

### Security Best Practices
- OIDC Trusted Publishing (no long-lived tokens)
- Digital attestations with Sigstore
- Branch protection enforcement
- No secrets required

## Example Output

When you invoke the agent, it will create/modify these files:

```
your-project/
├── .github/
│   └── workflows/
│       ├── ci.yml           # ← Created
│       └── release.yml      # ← Created
└── CONTRIBUTING.md          # ← Created or updated
```

And provide instructions for:
- Setting up PyPI Trusted Publishing
- Configuring branch protection
- Creating GitHub labels
- Testing the setup

## Real-World Usage

This is exactly how gs-batch-pdf was configured! The agent codifies all the lessons learned:

### CI Workflow
- Test on Python 3.12 and 3.13
- Type checking with mypy
- Build verification
- Ghostscript caching (60-70% faster)
- **Runtime:** ~30 seconds with cache hits

### Release Workflow
- Label-triggered: `release` + `bump:rc` (or other type)
- Automatic version bump and commit
- Publishes to PyPI (stable) or TestPyPI (pre-release)
- Creates GitHub Release with changelog
- **Runtime:** ~26 seconds

### Results
- First production release: v0.5.6 to PyPI ✅
- Test releases: Multiple to TestPyPI ✅
- CI time reduced: 3 minutes → 30 seconds (85% faster)
- Zero manual steps after PR merge

## Why This Approach Works

### For Maintainers
- ✅ No manual version editing - impossible to forget
- ✅ No manual tagging - automatic from version
- ✅ No manual publishing - triggered by label
- ✅ Clear audit trail - everything in git history
- ✅ Safe pre-release testing - TestPyPI first

### For Contributors
- ✅ Simple workflow - just add labels to PR
- ✅ Clear documentation - comprehensive guide
- ✅ Fast feedback - CI completes in ~30s
- ✅ Visible requirements - branch protection shows what's needed

### For Projects
- ✅ Consistent releases - same process every time
- ✅ Quality enforcement - CI must pass before release
- ✅ Security - no tokens in repository
- ✅ Transparency - everything visible in GitHub UI

## Customization

The agent adapts to your project:
- Different package managers (uv, poetry, pip)
- Different Python versions
- Different test frameworks
- External dependencies (databases, system packages)
- Type checkers (mypy, pyright, none)

## Limitations

The agent creates workflows but cannot:
- Configure PyPI Trusted Publishing (requires web UI)
- Set up branch protection rules (requires web UI)
- Create GitHub labels automatically (requires `gh` CLI)

It provides detailed instructions for these manual steps.

## Future Enhancements

Potential improvements to the agent:
- Support for monorepos
- Custom test commands
- Coverage reporting integration
- Slack/Discord notifications
- Automated changelog generation
- Multiple PyPI accounts

## Using It on Your Projects

1. Navigate to your Python project
2. Tell Claude Code: `Set up automated PyPI publishing`
3. Review the generated workflows
4. Follow the configuration guides
5. Test with a release to TestPyPI
6. Start using it for real releases!

## Success Stories

Projects using this approach:
- **gs-batch-pdf** - This project! First successful implementation
- *Your project here!* - Try it on your next Python package

## Questions?

The agent includes comprehensive troubleshooting sections for:
- CI failures
- Release workflow issues
- Branch protection problems
- PyPI publishing errors

Just ask Claude Code for help with any specific error message!

---

**Note:** The agent is in your global Claude config (`~/.claude/agents/setup-pypi-publishing.md`), so you can use it in any project without needing to copy it around.
