# Arch Linux package

This package installs the small, pure-Python TimbreDrop application. It does
not bundle a Python runtime, yt-dlp, FFmpeg, or Deno into a large standalone
executable; those are ordinary system dependencies installed by pacman.

The source is pinned to the upstream release tag `v0.1.4`. The PKGBUILD in
this project is for local testing and AUR preparation; it is not in the
official Arch repositories and has not yet been published to the AUR.

## Local build and test

Build only after the upstream `v0.1.4` tag exists and the source checksum in
the PKGBUILD has been replaced with the verified SHA-256 (the `SKIP` value is
temporary and must not be submitted to the AUR).

Install build tools:

```bash
sudo pacman -Syu --needed base-devel python-build python-installer python-setuptools python-pytest namcap
```

Copy the recipe to a clean package directory and build it:

```bash
mkdir -p ~/Projects/timbredrop-pkg
cp packaging/arch/PKGBUILD ~/Projects/timbredrop-pkg/PKGBUILD
cd ~/Projects/timbredrop-pkg
makepkg --syncdeps --cleanbuild
```

Inspect package metadata and install the locally built package:

```bash
namcap PKGBUILD timbredrop-0.1.4-1-any.pkg.tar.zst
ls -lh timbredrop-0.1.4-1-any.pkg.tar.zst
sudo pacman -U ./timbredrop-0.1.4-1-any.pkg.tar.zst

command -v ytmp3
ytmp3 --version
ytmp3
pacman -Qi timbredrop
```

To remove the test installation:

```bash
sudo pacman -R timbredrop
```

## Verify the upstream source checksum

After `v0.1.4` has been pushed, download the exact source archive and calculate
its checksum:

```bash
curl -fL 'https://github.com/not-koushi/timbredrop/archive/refs/tags/v0.1.4.tar.gz'   -o /tmp/timbredrop-0.1.4.tar.gz
sha256sum /tmp/timbredrop-0.1.4.tar.gz
```

Replace `sha256sums=('SKIP')` in the PKGBUILD with the resulting hash, then
rebuild with `makepkg --syncdeps --cleanbuild`. Do not publish an AUR recipe
with `SKIP` for this downloadable source archive.

## AUR publication (after local package testing)

The AUR hosts build recipes, not prebuilt binary packages. Before publishing,
confirm `timbredrop` is not already taken, verify the real source checksum,
build and install the package locally, and generate `.SRCINFO` from the final
PKGBUILD using `makepkg --printsrcinfo > .SRCINFO`. Publish `PKGBUILD` and
`.SRCINFO` to the separate AUR Git repository only after all checks pass.
