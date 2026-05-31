"""Enable `python -m creativeforge ...` as a fallback for the `creativeforge`
console script (handy on Windows when the venv's Scripts dir isn't on PATH)."""

from creativeforge.cli import app

if __name__ == "__main__":
    app()
