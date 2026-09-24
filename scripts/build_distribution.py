"""Build a clean, allowlisted source distribution without copying private state."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ["README.md", "CHANGELOG.md", "TEST-RESULTS.md", "pyproject.toml", ".gitignore",
             ".gitattributes", ".env.example", "Run-Local.ps1", "Run-Local.command"]
PATTERNS = ["src/tcg_lab/*.py", "src/pokelab/*.py", "src/tcg_lab/data/cards.json", "scripts/*.py", "tests/*.py",
            "docs/*.md", "examples/bully-box-demo.json", "web/package.json", "web/package-lock.json",
            "web/index.html", "web/*.ts", "web/tsconfig.json", "web/src/*.ts", "web/src/*.tsx",
            "web/src/*.css", "web/integration/*.ts", "web/prototype/*", "web/.figma/make/site.json"]


def build(root, output):
    paths = {root / name for name in TOP_FILES}
    for pattern in PATTERNS:
        paths.update(root.glob(pattern))
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or unsafe release file: {path.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            relative = path.relative_to(root)
            content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
            if path.suffix == ".ps1":
                content = content.replace("\n", "\r\n")
            info = ZipInfo("pokemon-tcg-lab/" + relative.as_posix())
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == ".command" else 0o100644) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content.encode("utf-8"))
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archive integrity check failed.")
    return len(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = build(ROOT, args.output.resolve())
    print(f"Created {args.output.resolve()} with {count} files in one pokemon-tcg-lab/ folder.")
