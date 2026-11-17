"""Validate local Markdown links without network access."""
from pathlib import Path
import re
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
errors = []
for document in [*root.glob("*.md"), *root.glob("docs/*.md")]:
    for link in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", document.read_text(encoding="utf-8")):
        if "://" in link or link.startswith(("#", "mailto:")):
            continue
        target = unquote(link.split("#", 1)[0])
        if target and not (document.parent / target).exists():
            errors.append(f"{document.relative_to(root)}: {link}")
if errors:
    raise SystemExit("Broken links:\n" + "\n".join(errors))
print("Local documentation links OK")
