"""Minimal check for a static site: index.html and 404.html exist, 404.html has the nav bar of index.html, every page parses and every local link, script, style and image it names exists, and the build publishes no design file or theme stylesheet a page does not load."""
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.found.append(value)


problems, pages, loaded = [], 0, set()
for folder, names, files in os.walk(ROOT):
    names[:] = [name for name in names if not name.startswith(".")]
    for name in files:
        if name.endswith(".html"):
            pages += 1
            path = os.path.join(folder, name)
            parser = Links()
            parser.feed(open(path, encoding="utf-8").read())
            for link in parser.found:
                parts = urlparse(link)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                target = os.path.join(ROOT, parts.path.lstrip("/")) if parts.path.startswith("/") else os.path.join(folder, unquote(parts.path))
                if not (os.path.isfile(target) or os.path.isfile(os.path.join(target, "index.html"))):
                    problems.append(f"{os.path.relpath(path, ROOT)} links to {link}, which does not exist")
                loaded.add(os.path.normpath(target))
stack = [path for path in loaded if path.endswith(".css")]
while stack:
    path = stack.pop()
    if os.path.isfile(path):
        for link in re.findall(r"""(?:@import\s+(?:url\()?|url\()\s*["']?([^"')\s;]+)""", open(path, encoding="utf-8").read()):
            parts = urlparse(link)
            target = os.path.normpath(os.path.join(os.path.dirname(path), unquote(parts.path)))
            if not (parts.scheme or parts.netloc) and target not in loaded:
                loaded.add(target)
                stack.append(target)
config = open(os.path.join(ROOT, "_config.yml"), encoding="utf-8").read() if os.path.isfile(os.path.join(ROOT, "_config.yml")) else ""
if not re.search(r"^theme:[ \t]*(null|~)[ \t]*$", config, re.M):
    problems.append("_config.yml must set theme: null, or Pages publishes the default theme's stylesheet")
block = re.search(r"^exclude:\n((?:[ \t]+-.*\n?)*)", config, re.M)
if not block:
    problems.append("_config.yml has no indented exclude list")
excluded = [os.path.join(ROOT, item) for item in re.findall(r"^[ \t]+-[ \t]+(\S+)", block.group(1) if block else "", re.M)]
for folder, names, files in os.walk(os.path.join(ROOT, "design")):
    for name in files:
        path = os.path.join(folder, name)
        if path not in loaded and not any(path == item or path.startswith(item + os.sep) for item in excluded):
            problems.append(f"{os.path.relpath(path, ROOT)} is published and no page loads it, so _config.yml must exclude it")
for required in ("index.html", "404.html"):
    if not os.path.isfile(os.path.join(ROOT, required)):
        problems.append(f"{required} is missing")
def bar(name):
    path = os.path.join(ROOT, name)
    found = re.search(r"<header class=\"navbar.*?</header>", open(path, encoding="utf-8").read(), re.S) if os.path.isfile(path) else None
    text = found.group(0) if found else ""
    return re.sub(r"\s+", " ", text.replace('href="/#', 'href="#').replace('href="/"', 'href="#main"').replace("/design/", "design/")).strip()


if os.path.isfile(os.path.join(ROOT, "404.html")) and os.path.isfile(os.path.join(ROOT, "index.html")) and bar("404.html") != bar("index.html"):
    problems.append("404.html must have the nav bar of index.html (design Pattern 2): same header, links to /#section and /")
print("\n".join(problems) or f"{pages} pages pass")
sys.exit(1 if problems else 0)
