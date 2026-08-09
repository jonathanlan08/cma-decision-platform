"""Seller-facing CMA report generation.

Renders a self-contained, print-optimized HTML document from a Jinja2 template.
If WeasyPrint (optional dependency with native libraries) is importable, the
same HTML is also converted to a PDF. The report contains no debugging output
or internal metadata beyond the calculation version, which is part of the
methodology disclosure.
"""
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..constants import CALC_VERSION, DISCLAIMER

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "$%s" % format(round(value), ",")


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "%+.1f%%" % (value * 100)


_env.filters["money"] = _money
_env.filters["pct"] = _pct


def render_report_html(context: Dict[str, Any]) -> str:
    context.setdefault("disclaimer", DISCLAIMER)
    context.setdefault("calc_version", CALC_VERSION)
    context.setdefault("generated_on", date.today().isoformat())
    template = _env.get_template("report.html")
    return template.render(**context)


def pdf_from_html(html: str) -> Optional[bytes]:
    """Return PDF bytes when WeasyPrint is available, else None (HTML export)."""
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return None
    return HTML(string=html).write_pdf()


def build_report_context(cma, comparables: List[Dict], valuation, strategies,
                         config) -> Dict[str, Any]:
    """Assemble the template context from already-computed values only;
    the report never calculates anything itself."""
    subject = cma.subject
    included = [c for c in comparables if c["included"]]
    excluded = [c for c in comparables if not c["included"]]
    return {
        "title": cma.title,
        "subject": subject,
        "comparables": comparables,
        "included": included,
        "excluded": excluded,
        "valuation": valuation,
        "strategies": strategies,
        "weights": config.weights if config else {},
        "assumptions": config.assumptions if config else {},
        "reconciliation": config.reconciliation if config else {},
    }
