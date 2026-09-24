"""PyInstaller entry point; independent of MCP startup."""
if __name__ == "__main__":
    try:
        from pokelab.desktop import main
        raise SystemExit(main())
    except Exception:
        import os
        from pathlib import Path
        import traceback
        log = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PokeLab" / "startup-error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        raise
