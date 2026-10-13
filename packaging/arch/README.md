# Arch Linux package

This `PKGBUILD` builds TimbreDrop from the tagged upstream source. It is intended for local testing before any AUR submission. It is not in the official Arch repositories, and it has not been published to the AUR.

## Prerequisite

The source tag matching `pkgver` must already exist in `not-koushi/timbredrop`. The packaging recipe currently targets `v0.1.2`. Publish the updated `0.1.2` source to GitHub and create the `v0.1.2` tag before building this recipe.

## Local build

```bash
sudo pacman -Syu --needed base-devel git python-build python-installer python-setuptools python-pytest
mkdir -p ~/Projects/timbredrop-pkg
cp packaging/arch/PKGBUILD ~/Projects/timbredrop-pkg/PKGBUILD
cd ~/Projects/timbredrop-pkg
makepkg --syncdeps --cleanbuild
```

Inspect and install the package you built:

```bash
less PKGBUILD
sudo pacman -U ./timbredrop-0.1.2-1-any.pkg.tar.zst
```

The installed package depends on Arch's `yt-dlp` package (which supplies `yt-dlp-ejs` as a dependency), FFmpeg, Deno and `python-platformdirs`. Recheck dependency names and versions on a fully updated Arch system before building.

To validate package metadata:

```bash
namcap PKGBUILD timbredrop-0.1.2-1-any.pkg.tar.zst
```

## AUR publication

The AUR uses a separate Git repository containing `PKGBUILD` and generated `.SRCINFO`; it is a community package source, not an official Arch package repository. Before publication, follow the current Arch package guidelines, ensure the upstream tag exists, build and test the package, then generate `.SRCINFO` with `makepkg --printsrcinfo > .SRCINFO`. Search the AUR for duplicate package names before creating an AUR repo. Do not publish until the package build has succeeded locally.
