"""Semantic version parsing and bumping utilities."""

from packaging.version import Version

# Default version for repositories with no tags
FIRST_RELEASE = "0.1.0"


class VersionError(Exception):
    """Raised when version operations fail."""

    pass


def parse_version(version_str: str) -> Version:
    """Parse a semantic version string.

    Args:
        version_str: Version string (e.g., '1.2.3')

    Returns:
        Parsed Version object

    Raises:
        VersionError: If version string is invalid
    """
    try:
        return Version(version_str)
    except Exception as e:
        raise VersionError(f"Invalid version string '{version_str}': {e}")


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump a semantic version by the specified type.

    Args:
        current_version: Current version string (e.g., '1.2.3')
        bump_type: Type of bump ('major', 'minor', or 'patch')

    Returns:
        New version string

    Raises:
        VersionError: If version or bump_type is invalid
    """
    version = parse_version(current_version)

    # Extract major, minor, patch from packaging.Version
    # Version.release is a tuple like (1, 2, 3)
    if len(version.release) < 3:
        raise VersionError(
            f"Version must have major.minor.patch format, got: {current_version}"
        )

    major, minor, patch = version.release[0], version.release[1], version.release[2]

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise VersionError(
            f"Invalid bump type '{bump_type}'. Must be 'major', 'minor', or 'patch'"
        )


def get_next_version(current_version: str | None, release_type: str | None) -> str:
    """Calculate the next version based on current version and release type.

    Args:
        current_version: Current version string or None if no releases yet
        release_type: Type of release ('major', 'minor', 'patch') or None if no changes

    Returns:
        Next version string

    Raises:
        VersionError: If version operations fail
    """
    # No release type means no relevant commits
    if release_type is None:
        if current_version is None:
            return FIRST_RELEASE
        return current_version

    # First release
    if current_version is None:
        return FIRST_RELEASE

    # Bump existing version
    return bump_version(current_version, release_type)
