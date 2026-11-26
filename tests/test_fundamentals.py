"""Tests for the Screener fundamentals parser (pure/offline)."""

from app.market_data.fundamentals import (
    annual_sales_cr_from_html,
    market_cap_cr_from_html,
    parse_screener_ratios,
)

# Minimal synthetic Screener markup mirroring the real structure.
_HTML = """
<html><body>
<ul id="top-ratios">
  <li class="flex flex-space-between">
    <span class="name">Market Cap</span>
    <span class="nowrap value"> ₹ <span class="number">16,45,678</span> Cr.</span>
  </li>
  <li class="flex flex-space-between">
    <span class="name">Current Price</span>
    <span class="nowrap value"> ₹ <span class="number">2,950</span></span>
  </li>
  <li class="flex flex-space-between">
    <span class="name">Stock P/E</span>
    <span class="nowrap value"><span class="number">28.4</span></span>
  </li>
  <li class="flex flex-space-between">
    <span class="name">High / Low</span>
    <span class="nowrap value"> ₹ <span class="number">3,100</span> / <span class="number">2,400</span></span>
  </li>
</ul>

<section id="profit-loss">
  <table class="data-table">
    <thead><tr><th></th><th>Mar 2023</th><th>Mar 2024</th><th>Mar 2025</th><th>TTM</th></tr></thead>
    <tbody>
      <tr><td class="text">Sales</td><td>90,000</td><td>1,05,000</td><td>1,20,000</td><td>1,25,000</td></tr>
      <tr><td class="text">Expenses</td><td>70,000</td><td>80,000</td><td>90,000</td><td>92,000</td></tr>
      <tr><td class="text">Net Profit</td><td>12,000</td><td>15,000</td><td>18,000</td><td>19,000</td></tr>
    </tbody>
  </table>
</section>
</body></html>
"""


def test_parse_ratios_extracts_named_values():
    ratios = parse_screener_ratios(_HTML)
    assert ratios["market cap"] == 1645678.0
    assert ratios["current price"] == 2950.0
    assert ratios["stock p/e"] == 28.4
    # High / Low takes the first number
    assert ratios["high / low"] == 3100.0


def test_market_cap_helper():
    assert market_cap_cr_from_html(_HTML) == 1645678.0


def test_annual_sales_takes_latest_column():
    # Latest column is TTM = 1,25,000
    assert annual_sales_cr_from_html(_HTML) == 125000.0


def test_missing_sections_safe():
    assert parse_screener_ratios("<html></html>") == {}
    assert market_cap_cr_from_html("<html></html>") is None
    assert annual_sales_cr_from_html("<html></html>") is None
