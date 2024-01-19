import datetime
import re

from hash import hashb


class FrontmatterEnricher:
    def __init__(self, content):
        self.original = content
        self.content = ("---\n---\n" + content) if not content.startswith("---") else content

    def enrich(self, *attributes):
        parts = self.content.split("---\n")
        attrs_added = False
        for attribute in attributes:
            new_attr = attribute(parts[1])
            if new_attr:
                attrs_added = True
            parts[1] += new_attr
        return "---\n".join(parts) if attrs_added else self.original

    def strip(self):
        parts = self.content.split("---\n")
        return "---\n".join(parts[2:])


def custom_edit_url(repo, file_path_rel_to_repo_root, branch):
    def inner(current_content):
        return (
            (
                f"custom_edit_url: https://github.com/PiwikPRO/{repo}/edit/{branch}"
                f"/{file_path_rel_to_repo_root}\n"
            )
            if "custom_edit_url" not in current_content
            else ""
        )

    return inner


def last_update(author):
    def inner(current_content):
        return (
            f"""last_update:
  date: {datetime.datetime.now().isoformat()}
  author: {author}\n"""
            if "last_update" not in current_content
            else ""
        )

    return inner


def source_frontmatter_hash(source_file):
    def inner(current_content):
        return (
            "x_source_frontmatter_hash: " + hashb(
                source_file.split("---\n")[1].encode("utf-8")
            ) + "\n"
        ) if source_file.startswith("---") else ""
    return inner


PATTERN = re.compile(r'.*x_source_frontmatter_hash:\s([a-z0-9]+)\n.*', re.DOTALL)


def get_source_frontmatter_hash(dest_frontmatter):
    match = PATTERN.match(dest_frontmatter)
    return match.group(1) if match else ""
