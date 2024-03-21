"""A mkdocs hook that injects an HTML syntax used to generate badges at build time."""

import re
from re import Match
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page


def on_page_markdown(markdown: str, *, page: Page, config: MkDocsConfig, files: Files):
    # Replace callback
    def replace(match: Match):
        badge_type, args = match.groups()
        args = args.strip()
        if badge_type == "version":
            return _badge_for_version(args, page, files)
        elif badge_type == "flag":
            return _badge_for_flags(args, page, files)
        elif badge_type == "permission":
            return _badge_for_permissions(args, page, files)
        elif badge_type == "default":
            return _badge_for_default(args, page, files)

        # Otherwise, raise an error
        raise RuntimeError(f"Unknown badge type: {badge_type}")

    # Find and replace all external asset URLs in current page
    return re.sub(r"<!-- md:(\w+) (.*) -->", replace, markdown, flags=re.I | re.M)


# -----------------------------------------------------------------------------
# Helper functions


def _badge_for_flags(arg, page: Page, files: Files):
    if arg == "experimental":
        return _badge_for_experimental(page, files)
    raise ValueError(f"Unsupported badge flag: {arg}")


# Create badge
def _badge(icon: str, text: str = ""):
    return "".join(
        [
            '<span class="mdx-badge">',
            *([f'<span class="mdx-badge__icon">{icon}</span>'] if icon else []),
            *([f'<span class="mdx-badge__text">{text}</span>'] if text else []),
            "</span>",
        ]
    )


# Create badge for version
def _badge_for_version(text: str, page: Page, files: Files):
    icon = "material-tag-outline"
    href = "https://github.com/cpp-linter/cpp-linter-action/releases/" + (
        f"v{text}" if text[0:1].isdigit() else text
    )
    return _badge(
        icon=f'[:{icon}:]({href} "minimum version")',
        text=f'[{text}]({href} "minimum version")',
    )


# Create badge for default value
def _badge_for_default(text: str, page: Page, files: Files):
    return _badge(icon="Default", text=f"`#!yaml {text}`")


# Create badge for required value flag
def _badge_for_permissions(args: str, page: Page, files: Files):
    match_permission = re.match(r"([^#]+)(.*)", args)
    if match_permission is None:
        raise ValueError(f"failed to parse permissions from {args}")
    permission, link = match_permission.groups()[:2]
    permission = permission.strip()
    link = "permissions.md" + link
    icon = "material-lock"
    return _badge(
        icon=f'[:{icon}:]({link} "required permissions")',
        text=f'[`#!yaml {permission}`]({link} "required permission")',
    )


# Create badge for experimental flag
def _badge_for_experimental(page: Page, files: Files):
    icon = "material-flask-outline"
    return _badge(icon=f":{icon}:{{ .mdx-badge--heart }}", text="experimental")
