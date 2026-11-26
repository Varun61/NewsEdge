"""Backtesting evaluation core.

The pure, dependency-free trade/cost/statistics model lives here so it can be
unit-tested offline. Data sourcing (filings history, price bars) and the run
orchestration live in ``scripts/`` and import from this package.
"""
