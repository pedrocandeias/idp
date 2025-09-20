from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Tuple

from jinja2 import BaseLoader, Environment

try:
    from weasyprint import HTML  # type: ignore
except Exception:  # pragma: no cover - optional in tests
    HTML = None  # type: ignore


BASE_CSS = """
/* Basic report styles */
body { font-family: DejaVu Sans, Arial, sans-serif; color: #222; }
.header { border-bottom: 2px solid #eee; margin-bottom: 12px; padding-bottom: 8px; }
.title { font-size: 20px; font-weight: bold; }
.meta { font-size: 12px; color: #666; }
.section { margin-top: 16px; }
.table { width: 100%; border-collapse: collapse; font-size: 12px; }
.table th, .table td { border: 1px solid #ddd; padding: 6px; }
.chart { height: 12px; background: #eee; border-radius: 6px; overflow: hidden; }
.bar { height: 12px; background: #2a9d8f; }
.footer { margin-top: 20px; font-size: 10px; color: #999; border-top: 1px solid #eee; padding-top: 8px; }
"""

TEMPLATE = """
<html>
<head>
  <meta charset='utf-8' />
  <style>{{ css }}</style>
</head>
<body>
  <div class="header">
    <div class="title">Inclusivity Evaluation Report</div>
    <div class="meta">Project: {{ project.name }} | Scenario: {{ scenario.name }} | Artifact: {{ artifact.name }} | RulePack: {{ rulepack.name if rulepack else 'N/A' }} v{{ rulepack.version if rulepack else '' }}</div>
    <div class="meta">Run ID: {{ run.id }} | Date: {{ date }}</div>
  </div>

  <div class="section">
    <h3>Inclusivity Index</h3>
    <div class="chart"><div class="bar" style="width: {{ (index.score*100)|round(1) }}%"></div></div>
    <div class="meta">Score: {{ (index.score*100)|round(1) }}% (reach {{ '✓' if index.components.reach else '✗' }}, strength {{ '✓' if index.components.strength else '✗' }}, visual {{ '✓' if index.components.visual else '✗' }})</div>
    {% if delta is not none %}
      <div class="meta">Change vs previous: {{ (delta*100)|round(1) }}%</div>
    {% endif %}
  </div>

  <div class="section">
    <h3>Findings</h3>
    <table class="table">
      <thead><tr><th>Rule</th><th>Outcome</th><th>Severity</th><th>Citation</th></tr></thead>
      <tbody>
      {% for r in results.rules %}
        <tr>
          <td>{{ r.id }}</td>
          <td>{{ 'PASS' if r.passed else 'FAIL' }}</td>
          <td>{{ r.severity }}</td>
          <td>{{ r.citation or '' }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="footer">
    SHA-256: {{ checksum }}
  </div>
</body>
</html>
"""


def render_html(context: dict) -> str:
    env = Environment(loader=BaseLoader(), autoescape=True)
    tmpl = env.from_string(TEMPLATE)
    html = tmpl.render(**context, css=BASE_CSS)
    return html


def render_pdf(html: str) -> bytes:
    if HTML is None:
        # Fallback for environments without WeasyPrint installed
        return html.encode("utf-8")
    return HTML(string=html).write_pdf()  # type: ignore


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
