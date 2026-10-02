"""Tests for docs/badge_hook.py, the mkdocs hook that renders ``<!-- md:... -->`` badges."""

from unittest.mock import MagicMock

import badge_hook
import pytest

RELEASES = "https://github.com/cpp-linter/cpp-linter-action/releases/"


def render(markdown: str) -> str:
    return badge_hook.on_page_markdown(
        markdown, page=MagicMock(), config=MagicMock(), files=MagicMock()
    )


def test_text_without_badges_is_unchanged():
    markdown = "# Title\n\n<!-- a regular comment -->\nSome `code`.\n"
    assert render(markdown) == markdown


def test_version_badge_links_to_the_release_tag():
    href = RELEASES + "v1.2.0"
    assert render("<!-- md:version 1.2.0 -->") == (
        '<span class="mdx-badge">'
        f'<span class="mdx-badge__icon">[:material-tag-outline:]({href} "minimum version")</span>'
        f'<span class="mdx-badge__text">[1.2.0]({href} "minimum version")</span>'
        "</span>"
    )


def test_version_badge_keeps_a_non_numeric_ref():
    assert f"({RELEASES}latest " in render("<!-- md:version latest -->")
    assert "/vlatest" not in render("<!-- md:version latest -->")


def test_default_badge_shows_the_value_as_yaml():
    assert render("<!-- md:default 'llvm' -->") == (
        '<span class="mdx-badge">'
        '<span class="mdx-badge__icon">Default</span>'
        "<span class=\"mdx-badge__text\">`#!yaml 'llvm'`</span>"
        "</span>"
    )


def test_permission_badge_links_to_the_permission_section():
    assert render("<!-- md:permission contents: read #file-changes -->") == (
        '<span class="mdx-badge">'
        '<span class="mdx-badge__icon">'
        '[:material-lock:](permissions.md#file-changes "required permissions")</span>'
        '<span class="mdx-badge__text">'
        '[`#!yaml contents: read`](permissions.md#file-changes "required permission")</span>'
        "</span>"
    )


def test_permission_badge_without_anchor_links_to_the_page():
    rendered = render("<!-- md:permission pull-requests: write -->")
    assert '(permissions.md "required permissions")' in rendered
    assert "[`#!yaml pull-requests: write`](permissions.md " in rendered


def test_experimental_flag_badge():
    assert render("<!-- md:flag experimental -->") == (
        '<span class="mdx-badge">'
        '<span class="mdx-badge__icon">:material-flask-outline:{ .mdx-badge--heart }</span>'
        '<span class="mdx-badge__text">experimental</span>'
        "</span>"
    )


def test_badges_are_replaced_on_every_line():
    rendered = render(
        "### `style`\n\n"
        "<!-- md:version 1.2.0 -->\n"
        "<!-- MD:default 'llvm' -->\n"  # the marker is matched case-insensitively
        "\nThe style rules to use.\n"
    )
    assert "<!--" not in rendered
    assert rendered.startswith("### `style`\n\n<span")
    assert rendered.endswith("</span>\n\nThe style rules to use.\n")
    assert rendered.count('<span class="mdx-badge">') == 2


def test_unknown_badge_type_is_an_error():
    with pytest.raises(RuntimeError, match="Unknown badge type: deprecated"):
        render("<!-- md:deprecated 2.0.0 -->")


def test_unsupported_flag_is_an_error():
    with pytest.raises(ValueError, match="Unsupported badge flag: beta"):
        render("<!-- md:flag beta -->")


def test_permission_without_a_name_is_an_error():
    with pytest.raises(ValueError, match="failed to parse permissions from #anchor"):
        render("<!-- md:permission #anchor -->")


@pytest.mark.parametrize(
    ("icon", "text", "expected"),
    [
        (
            "i",
            "t",
            '<span class="mdx-badge__icon">i</span><span class="mdx-badge__text">t</span>',
        ),
        ("i", "", '<span class="mdx-badge__icon">i</span>'),
        ("", "t", '<span class="mdx-badge__text">t</span>'),
        ("", "", ""),
    ],
    ids=["icon-and-text", "icon-only", "text-only", "empty"],
)
def test_badge_omits_empty_parts(icon: str, text: str, expected: str):
    assert badge_hook._badge(icon, text) == f'<span class="mdx-badge">{expected}</span>'
