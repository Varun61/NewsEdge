"""Direct runner script for the daily batch pipeline.

Usage:
    python -m scripts.run_pipeline
    python -m scripts.run_pipeline --date 2026-11-02
"""

from app.pipeline import main

if __name__ == "__main__":
    main()
