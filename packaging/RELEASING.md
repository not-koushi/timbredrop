# Maintainer release checklist

This repository is prepared for the first tagged binary release. Do not create a release tag until the source changes below are pushed and CI is green.

1. Apply and review the packaging changes locally.
2. Run `pytest -q`, `ruff check .`, and `python -m build --wheel`.
3. Commit and push the complete source tree to `main`; confirm the GitHub Actions CI workflow passes on all operating systems.
4. Verify that `pyproject.toml` and `src/timbredrop/__init__.py` both contain the intended release version `0.1.2`.
5. Create and push the tag:

   ```bash
   git tag -a v0.1.2 -m "TimbreDrop 0.1.2"
   git push origin v0.1.2
   ```

6. The release workflow builds native one-file executables on Linux, Windows, macOS Intel, and macOS Apple Silicon. Each executable must pass its `--version` smoke test. The publish job attaches each platform ZIP to a GitHub release.
7. Open the Actions tab and verify the `Release binaries` workflow and the generated GitHub release. Do not claim downloads are available unless the workflow succeeds.
8. For the Arch package, copy `packaging/arch/PKGBUILD` into a separate packaging directory, run `makepkg --syncdeps --cleanbuild`, inspect the package, and only then consider an AUR submission.

The release archives bundle the Python CLI, yt-dlp, and yt-dlp-ejs. FFmpeg/FFprobe and Deno remain separately installed runtime dependencies. Cross-platform unit tests and a `--version` smoke test do not prove that live YouTube extraction works on every platform; manually test a permitted video on each target OS before making stronger claims.
