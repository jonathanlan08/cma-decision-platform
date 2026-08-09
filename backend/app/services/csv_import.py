"""CSV comparable import with row-level validation.

Strict header contract (see data/sample/comparables_template.csv). Invalid rows
are rejected individually with field-level messages; valid rows import. The
importer never guesses at ambiguous values.
"""
import csv
import io
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..constants import (
    CONDITION_SCALE,
    CSV_MAX_ROWS,
    CSV_REQUIRED_COLUMNS,
    PROPERTY_TYPES,
)

TRUE_VALUES = {"true", "yes", "y", "1"}
FALSE_VALUES = {"false", "no", "n", "0", ""}


def template_csv() -> str:
    """Downloadable template: header plus one illustrative synthetic row."""
    from ..constants import CSV_COLUMNS
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    writer.writerow([
        "1234 Example St", "Arcadia", "91006", "34.1397", "-118.0353",
        "single_family", "1250000", "2026-05-15", "1850", "7200", "3", "2",
        "1955", "good", "2", "false", "0.8",
        "Synthetic example row - replace with real data", "synthetic-demo",
    ])
    return buf.getvalue()


def _parse_float(value: str, field: str, errors: List[Dict], row: int,
                 minimum: Optional[float] = None, required: bool = False,
                 strictly_positive: bool = False) -> Optional[float]:
    value = (value or "").strip().replace("$", "").replace(",", "")
    if value == "":
        if required:
            errors.append({"row": row, "field": field, "message": "%s is required" % field})
        return None
    try:
        parsed = float(value)
    except ValueError:
        errors.append({"row": row, "field": field,
                       "message": "'%s' is not a valid number" % value})
        return None
    if strictly_positive and parsed <= 0:
        errors.append({"row": row, "field": field,
                       "message": "%s must be greater than zero" % field})
        return None
    if minimum is not None and parsed < minimum:
        errors.append({"row": row, "field": field,
                       "message": "%s must be at least %s" % (field, minimum)})
        return None
    return parsed


def _parse_int(value: str, field: str, errors: List[Dict], row: int,
               minimum: Optional[int] = None, required: bool = False) -> Optional[int]:
    parsed = _parse_float(value, field, errors, row, required=required)
    if parsed is None:
        return None
    if parsed != int(parsed):
        errors.append({"row": row, "field": field,
                       "message": "%s must be a whole number" % field})
        return None
    result = int(parsed)
    if minimum is not None and result < minimum:
        errors.append({"row": row, "field": field,
                       "message": "%s must be at least %d" % (field, minimum)})
        return None
    return result


def _parse_date(value: str, field: str, errors: List[Dict], row: int) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        errors.append({"row": row, "field": field, "message": "%s is required" % field})
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            break
        except ValueError:
            parsed = None
    if parsed is None:
        errors.append({"row": row, "field": field,
                       "message": "'%s' is not a valid date (use YYYY-MM-DD)" % value})
        return None
    if parsed > date.today():
        errors.append({"row": row, "field": field, "message": "sale_date is in the future"})
        return None
    return parsed


def parse_comparables_csv(text: str) -> Tuple[List[Dict], List[Dict]]:
    """Return (valid_rows, errors). Row numbers are 1-based data rows
    (header excluded) so they match what a spreadsheet user sees minus one."""
    errors: List[Dict] = []
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], [{"row": 0, "field": "file", "message": "File is empty"}]

    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [col for col in CSV_REQUIRED_COLUMNS if col not in headers]
    if missing:
        return [], [{"row": 0, "field": "header",
                     "message": "Missing required column(s): %s" % ", ".join(missing)}]

    valid: List[Dict] = []
    for idx, raw in enumerate(reader, start=1):
        if idx > CSV_MAX_ROWS:
            errors.append({"row": idx, "field": "file",
                           "message": "Row limit of %d exceeded; extra rows ignored"
                           % CSV_MAX_ROWS})
            break
        row = { (k or "").strip().lower(): (v or "").strip() for k, v in raw.items() }
        row_errors: List[Dict] = []

        address = row.get("address", "")
        if not address:
            row_errors.append({"row": idx, "field": "address", "message": "address is required"})

        sale_price = _parse_float(row.get("sale_price", ""), "sale_price", row_errors, idx,
                                  required=True, strictly_positive=True)
        sale_date = _parse_date(row.get("sale_date", ""), "sale_date", row_errors, idx)
        square_feet = _parse_float(row.get("square_feet", ""), "square_feet", row_errors, idx,
                                   required=True, strictly_positive=True)
        bedrooms = _parse_int(row.get("bedrooms", ""), "bedrooms", row_errors, idx,
                              minimum=0, required=True)
        bathrooms = _parse_float(row.get("bathrooms", ""), "bathrooms", row_errors, idx,
                                 minimum=0, required=True)

        latitude = _parse_float(row.get("latitude", ""), "latitude", row_errors, idx)
        if latitude is not None and not -90 <= latitude <= 90:
            row_errors.append({"row": idx, "field": "latitude",
                               "message": "latitude must be between -90 and 90"})
            latitude = None
        longitude = _parse_float(row.get("longitude", ""), "longitude", row_errors, idx)
        if longitude is not None and not -180 <= longitude <= 180:
            row_errors.append({"row": idx, "field": "longitude",
                               "message": "longitude must be between -180 and 180"})
            longitude = None

        lot_size = _parse_float(row.get("lot_size", ""), "lot_size", row_errors, idx, minimum=0)
        year_built = _parse_int(row.get("year_built", ""), "year_built", row_errors, idx)
        if year_built is not None and not 1800 <= year_built <= date.today().year + 1:
            row_errors.append({"row": idx, "field": "year_built",
                               "message": "year_built %d is out of range" % year_built})
            year_built = None
        parking_spaces = _parse_int(row.get("parking_spaces", ""), "parking_spaces",
                                    row_errors, idx, minimum=0)
        distance = _parse_float(row.get("distance_from_subject", ""), "distance_from_subject",
                                row_errors, idx, minimum=0)

        condition = row.get("condition", "").lower() or None
        if condition is not None and condition not in CONDITION_SCALE:
            row_errors.append({"row": idx, "field": "condition",
                               "message": "condition must be one of: %s"
                               % ", ".join(CONDITION_SCALE)})
            condition = None

        property_type = row.get("property_type", "").lower() or "single_family"
        if property_type not in PROPERTY_TYPES:
            row_errors.append({"row": idx, "field": "property_type",
                               "message": "property_type must be one of: %s"
                               % ", ".join(PROPERTY_TYPES)})

        pool_raw = row.get("pool", "").lower()
        if pool_raw in TRUE_VALUES:
            has_pool = True
        elif pool_raw in FALSE_VALUES:
            has_pool = False
        else:
            row_errors.append({"row": idx, "field": "pool",
                               "message": "'%s' is not a valid true/false value" % pool_raw})
            has_pool = False

        if row_errors:
            errors.extend(row_errors)
            continue

        valid.append({
            "address": address,
            "city": row.get("city") or None,
            "zip_code": row.get("zip_code") or None,
            "latitude": latitude,
            "longitude": longitude,
            "property_type": property_type,
            "sale_price": sale_price,
            "sale_date": sale_date,
            "square_feet": square_feet,
            "lot_size": lot_size,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "year_built": year_built,
            "condition": condition,
            "parking_spaces": parking_spaces,
            "has_pool": has_pool,
            "distance_from_subject": distance,
            "notes": row.get("notes") or None,
            "source": row.get("source") or "csv-upload",
        })

    return valid, errors
