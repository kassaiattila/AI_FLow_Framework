"""Platform-specific selectors and navigation logic."""

from __future__ import annotations

from skills.cubix_course_capture.platforms.base import PlatformConfig
from skills.cubix_course_capture.platforms.cubixedu import CUBIXEDU_CONFIG

__all__ = ["PlatformConfig", "CUBIXEDU_CONFIG", "get_platform_config"]


def get_platform_config(platform: str = "cubixedu") -> PlatformConfig:
    """Get the platform configuration by name.

    Args:
        platform: Platform identifier (cubixedu, udemy, coursera, etc.).

    Returns:
        PlatformConfig for the requested platform.

    Raises:
        ValueError: If the platform is not supported.
    """
    configs: dict[str, PlatformConfig] = {
        "cubixedu": CUBIXEDU_CONFIG,
    }
    if platform not in configs:
        available = list(configs.keys())
        raise ValueError(f"Unknown platform: {platform}. Available: {available}")
    return configs[platform]
