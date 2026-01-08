# Publishing to PyPI

This document explains how to publish `adk-skills-agent` to PyPI.

## Prerequisites

### 1. Set up PyPI Trusted Publishing

PyPI now supports "Trusted Publishing" which uses OpenID Connect (OIDC) to authenticate GitHub Actions workflows. This is more secure than using API tokens.

#### Steps to enable Trusted Publishing:

1. **Go to PyPI** (for production) or **Test PyPI** (for testing):
   - PyPI: https://pypi.org
   - Test PyPI: https://test.pypi.org

2. **Create the project** (if it doesn't exist yet):
   - Go to "Your projects" → "Publishing"
   - Or navigate to: https://pypi.org/manage/account/publishing/

3. **Add a new pending publisher**:
   - **PyPI project name**: `adk-skills-agent`
   - **Owner**: `manojlds` (your GitHub username/org)
   - **Repository name**: `adk-skills`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi` (for production) or `testpypi` (for test)

4. **Repeat for Test PyPI**:
   - Same steps at https://test.pypi.org/manage/account/publishing/
   - Use environment name: `testpypi`

### 2. Create GitHub Environments

Create environments in your GitHub repository to add approval gates:

1. Go to your repository → Settings → Environments
2. Create two environments:
   - **pypi**: For production releases (add protection rules if needed)
   - **testpypi**: For testing releases

## Publishing Methods

### Method 1: Automatic on GitHub Release (Recommended)

1. **Update version** in both files:
   - `pyproject.toml`: Update the `version` field
   - `adk_skills/__init__.py`: Update `__version__`

2. **Create a GitHub Release**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
   - Or use GitHub UI: Releases → Create new release
   - Tag: `v0.1.0`
   - Title: `v0.1.0`
   - Description: Release notes

3. The workflow will automatically:
   - Build the package
   - Publish to PyPI

### Method 2: Manual Workflow Dispatch

For testing or manual releases:

1. Go to Actions → Publish to PyPI → Run workflow
2. Choose environment:
   - **testpypi**: For testing (publishes to test.pypi.org)
   - **pypi**: For production (publishes to pypi.org)

## Testing Before Publishing

### Test with Test PyPI:

1. **Run the workflow manually** with `testpypi` environment
2. **Install from Test PyPI** to verify:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ adk-skills-agent
   ```

3. **Test the installation** to ensure everything works

### Local Build Test:

```bash
# Build the package locally
python -m pip install build
python -m build

# Check the built files
ls dist/
# Should see: adk_skills_agent-0.1.0.tar.gz and adk_skills_agent-0.1.0-py3-none-any.whl

# Install locally to test
pip install dist/adk_skills_agent-0.1.0-py3-none-any.whl
```

## Version Management

**IMPORTANT**: Keep versions in sync in both files:

1. `pyproject.toml`:
   ```toml
   [project]
   version = "0.1.0"
   ```

2. `adk_skills/__init__.py`:
   ```python
   __version__ = "0.1.0"
   ```

### Version Numbering:

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

For pre-releases:
- `0.1.0a1` - Alpha release
- `0.1.0b1` - Beta release
- `0.1.0rc1` - Release candidate

## Workflow Overview

The `publish.yml` workflow:

1. **Triggers**:
   - On GitHub release creation (automatic)
   - Manual workflow dispatch (for testing)

2. **Jobs**:
   - **build**: Builds the distribution packages
   - **publish-to-pypi**: Publishes to production PyPI
   - **publish-to-testpypi**: Publishes to Test PyPI

3. **Security**:
   - Uses trusted publishing (OIDC)
   - No API tokens needed
   - Scoped to specific environments

## Troubleshooting

### "Project not found" error:
- Ensure you've set up the pending publisher on PyPI
- Check the project name matches exactly: `adk-skills-agent`

### "Permission denied" error:
- Verify GitHub environments are created
- Check the workflow has `id-token: write` permission

### "Version already exists" error:
- PyPI doesn't allow re-uploading the same version
- Increment the version number
- Use Test PyPI for testing

## Resources

- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions PyPI Publish](https://github.com/marketplace/actions/pypi-publish)
- [Python Packaging Guide](https://packaging.python.org/)

## Checklist for First Release

- [ ] Set up PyPI trusted publishing for `adk-skills-agent`
- [ ] Set up Test PyPI trusted publishing for testing
- [ ] Create GitHub environments: `pypi` and `testpypi`
- [ ] Update version to `0.1.0` (or desired version)
- [ ] Test build locally: `python -m build`
- [ ] Test publish to Test PyPI
- [ ] Test install from Test PyPI
- [ ] Create GitHub release with tag `v0.1.0`
- [ ] Verify automatic publish to PyPI
- [ ] Test install from PyPI: `pip install adk-skills-agent`
- [ ] Update README if needed
