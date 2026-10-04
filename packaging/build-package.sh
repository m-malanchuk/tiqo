#!/usr/bin/env bash

# Build and install the local Arch package from the current Git commit.
# Run this script as a normal user, from any directory:
#   ./packaging/build-package.sh
# It uses sudo only when pacman needs system privileges.

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
PACKAGING_DIR="${ROOT_DIR}/packaging"
PKGBUILD_PATH="${PACKAGING_DIR}/PKGBUILD"
PKG_NAME=$(sed -n "s/^pkgname=['\"]\?\([^'\"]*\)['\"]\?$/\1/p" "${PKGBUILD_PATH}")
PKG_VERSION=$(sed -n "s/^pkgver=['\"]\?\([^'\"]*\)['\"]\?$/\1/p" "${PKGBUILD_PATH}")
SOURCE_ARCHIVE="${PACKAGING_DIR}/${PKG_NAME}-${PKG_VERSION}.tar.gz"

if [[ ${EUID} -eq 0 ]]; then
    printf '%s\n' "Do not run this script with sudo. Run it as your normal user; it calls sudo only for pacman." >&2
    exit 1
fi

for command_name in git makepkg pacman sudo; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        printf 'Missing command: %s\n' "${command_name}" >&2
        exit 1
    fi
done

if [[ ! -f ${PKGBUILD_PATH} ]]; then
    printf 'PKGBUILD not found: %s\n' "${PKGBUILD_PATH}" >&2
    exit 1
fi

cleanup() {
    rm -f -- "${SOURCE_ARCHIVE}"
}
trap cleanup EXIT

cd -- "${ROOT_DIR}"

if [[ -n $(git status --porcelain=v1 --untracked-files=all) ]]; then
    printf '%s\n' 'Working tree is not clean. Commit all project files before building the package.' >&2
    exit 1
fi

printf '%s\n' 'Installing Arch build/runtime dependencies...'
sudo pacman -S --needed --noconfirm \
    python \
    pyside6 \
    python-build \
    python-hatchling \
    python-installer

printf '%s\n' 'Creating source archive from the current Git commit...'
git archive \
    --format=tar.gz \
    --prefix="${PKG_NAME}-${PKG_VERSION}/" \
    --output="${SOURCE_ARCHIVE}" \
    HEAD

printf '%s\n' 'Building and installing the package...'
(
    cd -- "${PACKAGING_DIR}"
    makepkg --clean --force --syncdeps --install --noconfirm -p PKGBUILD
)

printf '\nPackage installed successfully.\n'
printf 'Name: %s\nVersion: %s\n' "${PKG_NAME}" "${PKG_VERSION}"
printf 'Verify widget files with:\n  test -d /usr/share/plasma/plasmoids/org.tiqo.work\n'

