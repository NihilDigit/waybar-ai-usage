#!/usr/bin/env bash
#
# Release automation script for waybar-ai-usage
# Handles version bumping, GitHub releases, and AUR package updates
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYPROJECT="${REPO_ROOT}/pyproject.toml"
PKGBUILD="${REPO_ROOT}/aur/waybar-ai-usage/PKGBUILD"
SRCINFO="${REPO_ROOT}/aur/waybar-ai-usage/.SRCINFO"
LOCKFILE="${REPO_ROOT}/uv.lock"
GITHUB_REPO="NihilDigit/waybar-ai-usage"
AUR_REPO="ssh://aur@aur.archlinux.org/waybar-ai-usage.git"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Get current version from pyproject.toml
get_current_version() {
    grep '^version = ' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/'
}

# Update version in pyproject.toml
update_pyproject_version() {
    local new_version="$1"
    sed -i "s/^version = .*/version = \"${new_version}\"/" "$PYPROJECT"
}

# Update version in PKGBUILD
update_pkgbuild_version() {
    local new_version="$1"
    sed -i "s/^pkgver=.*/pkgver=${new_version}/" "$PKGBUILD"
    sed -i "s/^pkgrel=.*/pkgrel=1/" "$PKGBUILD"
}

# Refresh uv.lock so the version it records follows pyproject.toml. Editing the
# lockfile with sed would hit every package's version field, so let uv rewrite it.
update_lockfile() {
    if ! command -v uv >/dev/null 2>&1; then
        log_warn "uv not found, leaving uv.lock at its current version"
        return
    fi
    log_info "Refreshing uv.lock..."
    (cd "$REPO_ROOT" && uv lock --quiet)
}

# Download tarball and calculate checksum
update_pkgbuild_checksum() {
    local version="$1"
    local tarball_url="https://api.github.com/repos/${GITHUB_REPO}/tarball/refs/tags/v${version}"
    local tmp_tarball="/tmp/waybar-ai-usage-${version}.tar.gz"

    log_info "Downloading tarball from GitHub..."
    curl -L -o "$tmp_tarball" "$tarball_url"

    log_info "Calculating SHA256 checksum..."
    local checksum
    checksum=$(sha256sum "$tmp_tarball" | awk '{print $1}')

    log_info "Checksum: $checksum"
    sed -i "s/^sha256sums=.*/sha256sums=('${checksum}')/" "$PKGBUILD"

    rm -f "$tmp_tarball"
}

# Generate .SRCINFO
generate_srcinfo() {
    log_info "Generating .SRCINFO..."
    (cd "$(dirname "$PKGBUILD")" && makepkg --printsrcinfo > .SRCINFO)
}

# Commit and tag
git_commit_and_tag() {
    local version="$1"
    local commit_msg="$2"

    log_info "Staging changes..."
    git add "$PYPROJECT" "$PKGBUILD" "$SRCINFO" "$LOCKFILE"

    log_info "Creating commit..."
    git commit -m "$commit_msg"

    log_info "Creating tag v${version}..."
    git tag -a "v${version}" -m "Release v${version}"
}

# Push to GitHub
push_to_github() {
    log_info "Pushing to GitHub..."
    git push origin main
    git push origin --tags
}

# Push to AUR
push_to_aur() {
    local aur_tmpdir
    aur_tmpdir=$(mktemp -d)

    log_info "Cloning AUR repository to $aur_tmpdir..."
    git clone "$AUR_REPO" "$aur_tmpdir"

    log_info "Copying files to AUR repository..."
    cp "$PKGBUILD" "$SRCINFO" "$aur_tmpdir/"

    log_info "Committing to AUR..."
    (
        cd "$aur_tmpdir"
        git add PKGBUILD .SRCINFO
        git commit -m "Update to $1"
        git push
    )

    log_info "Cleaning up temporary directory..."
    rm -rf "$aur_tmpdir"
}

# Exercise the local half of a release and roll it back. Steps 4 onward need the
# tag to exist on GitHub, so the checksum and .SRCINFO stay unverified here.
do_dry_run() {
    local new_version="$1"

    log_info "Dry run for ${new_version}: local edits only, nothing is committed or pushed"
    update_pyproject_version "$new_version"
    update_pkgbuild_version "$new_version"
    update_lockfile

    echo ""
    git --no-pager diff -- "$PYPROJECT" "$PKGBUILD" "$LOCKFILE"
    echo ""

    log_info "Reverting the working tree..."
    git restore -- "$PYPROJECT" "$PKGBUILD" "$LOCKFILE"
    log_success "Dry run complete"
    log_warn "Not covered: the tarball checksum and .SRCINFO, both of which need the tag on GitHub"
}

# Step 7 on its own, for when the AUR push is the only thing left — an AUR
# outage, an expired SSH key, a rejected PKGBUILD. Everything it needs is
# already committed by then.
do_aur_only() {
    local version="$1"
    local pkgver
    pkgver=$(grep '^pkgver=' "$PKGBUILD" | cut -d= -f2)

    if [[ "$pkgver" != "$version" ]]; then
        log_error "PKGBUILD is at ${pkgver}, not ${version}"
        log_error "Run the full release first; this mode only republishes what is already committed."
        exit 1
    fi

    log_info "Publishing ${version} to AUR from the committed PKGBUILD and .SRCINFO"
    echo ""
    read -p "Proceed? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Cancelled."
        exit 0
    fi

    push_to_aur "$version"
    log_success "Pushed to AUR"
    log_info "AUR package: https://aur.archlinux.org/packages/waybar-ai-usage"
}

# Main release function
do_release() {
    local new_version="$1"
    local current_version
    current_version=$(get_current_version)

    log_info "Current version: $current_version"
    log_info "New version: $new_version"

    # Confirmation
    echo ""
    read -p "Proceed with release? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Release cancelled."
        exit 0
    fi

    # Step 1: Update versions
    log_info "Step 1/7: Updating version numbers..."
    update_pyproject_version "$new_version"
    update_pkgbuild_version "$new_version"
    update_lockfile
    log_success "Version numbers updated"

    # Step 2: Commit and tag (without checksum first)
    log_info "Step 2/7: Creating initial commit and tag..."
    git_commit_and_tag "$new_version" "chore: bump version to ${new_version}"
    log_success "Commit and tag created"

    # Step 3: Push to GitHub
    log_info "Step 3/7: Pushing to GitHub..."
    push_to_github
    log_success "Pushed to GitHub"

    # Step 4: Wait for GitHub to process the tag
    log_info "Step 4/7: Waiting for GitHub to process the release..."
    sleep 5

    # Step 5: Update PKGBUILD with correct checksum
    log_info "Step 5/7: Updating PKGBUILD checksum..."
    update_pkgbuild_checksum "$new_version"
    generate_srcinfo
    log_success "PKGBUILD checksum updated"

    # Step 6: Commit AUR updates
    log_info "Step 6/7: Committing AUR package updates..."
    git add "$PKGBUILD" "$SRCINFO"
    git commit -m "chore: update AUR package to ${new_version}"
    git push origin main
    log_success "AUR package files committed to GitHub"

    # Step 7: Push to AUR
    log_info "Step 7/7: Pushing to AUR..."
    push_to_aur "$new_version"
    log_success "Pushed to AUR"

    echo ""
    log_success "Release ${new_version} completed successfully!"
    echo ""
    log_info "GitHub release: https://github.com/${GITHUB_REPO}/releases/tag/v${new_version}"
    log_info "AUR package: https://aur.archlinux.org/packages/waybar-ai-usage"
    echo ""
}

# Parse command line arguments
usage() {
    local current_version
    current_version=$(get_current_version)
    echo "waybar-ai-usage release script"
    echo ""
    echo "Current version: $current_version"
    echo ""
    echo "Usage: $0 [--dry-run | --aur-only] <version>"
    echo ""
    echo "  (no flag)     full release: bump, tag, push to GitHub, push to AUR"
    echo "  --dry-run     apply the version bump locally, show the diff, revert"
    echo "  --aur-only    push an already-released version to AUR"
    echo ""
    echo "Example: $0 0.4.1"
}

main() {
    cd "$REPO_ROOT"

    local mode="release"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)  mode="dry-run";  shift ;;
            --aur-only) mode="aur-only"; shift ;;
            -h|--help)  usage; exit 0 ;;
            -*)         log_error "Unknown option: $1"; echo ""; usage; exit 1 ;;
            *)          break ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        usage
        exit 1
    fi

    local new_version="$1"

    # Validate version format (basic semver)
    if [[ ! $new_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format: $new_version"
        log_error "Expected format: X.Y.Z (e.g., 0.4.1)"
        exit 1
    fi

    # Check if working directory is clean
    if [[ -n $(git status --porcelain) ]]; then
        log_error "Working directory is not clean. Commit or stash changes first."
        git status --short
        exit 1
    fi

    # Check if we're on main branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        log_warn "Not on main branch (current: $current_branch)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    case "$mode" in
        dry-run)  do_dry_run  "$new_version" ;;
        aur-only) do_aur_only "$new_version" ;;
        release)  do_release  "$new_version" ;;
    esac
}

main "$@"
