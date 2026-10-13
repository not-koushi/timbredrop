# Maintainer release checklist

## Source/AUR version release

1. Update `pyproject.toml`, `src/timbredrop/__init__.py`, and `CHANGELOG.md` to
   the same version.
2. Run `pytest -q`, `ruff check .`, and `python -m build --wheel`.
3. Commit and push source plus packaging changes to `main`; confirm the CI
   workflow passes.
4. Check that the Arch PKGBUILD targets the same `v<version>` source tag.
5. Push the matching source tag (for this packaging preparation, `v0.1.4`).
6. Verify the source tag and build the Arch package locally before AUR
   submission. The AUR recipe must contain a real SHA-256 checksum, not `SKIP`.

## Optional standalone binary release

The standalone ZIPs bundle a Python runtime and yt-dlp resources, so they are
much larger than the pure-Python Arch package. Tags no longer automatically
build/publish these ZIPs. To intentionally publish native standalone binaries
for an existing version, manually dispatch the **Release binaries** workflow
from `main`, passing the matching tag as `release_tag`. For example:

```bash
gh workflow run release.yml --ref main -f release_tag=v0.1.4
```

The workflow builds on each target operating system. A successful build and a
`--version` smoke test do not prove that live YouTube extraction works on every
platform; test a permitted video on each OS before making stronger claims.
