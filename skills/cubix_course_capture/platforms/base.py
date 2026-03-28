"""Base platform configuration model."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["PlatformConfig", "SelectorSet"]


class SelectorSet(BaseModel):
    """CSS selectors for a specific page/action.

    Groups related selectors together (e.g., all login form selectors,
    all video player selectors) for clean platform configuration.
    """

    selectors: dict[str, str] = Field(default_factory=dict)

    def get(self, key: str) -> str:
        """Get a CSS selector by key.

        Args:
            key: Selector identifier within this set.

        Returns:
            The CSS selector string.

        Raises:
            KeyError: If the selector key is not defined.
        """
        if key not in self.selectors:
            raise KeyError(f"Selector '{key}' not defined in this set")
        return self.selectors[key]


class PlatformConfig(BaseModel):
    """Platform-specific configuration with all CSS selectors.

    Each supported platform (cubixedu, udemy, coursera) provides its own
    PlatformConfig instance with the correct selectors and JavaScript
    snippets for course scanning and video detection.
    """

    name: str
    display_name: str
    base_url: str
    login_url: str

    # Selector sets for different page areas
    cookie_consent: SelectorSet = Field(default_factory=SelectorSet)
    login: SelectorSet = Field(default_factory=SelectorSet)
    structure: SelectorSet = Field(default_factory=SelectorSet)
    video: SelectorSet = Field(default_factory=SelectorSet)

    # JavaScript snippets for browser-side scanning
    scan_structure_js: str = ""
    get_video_info_js: str = ""
