"""CSV import validation: template/sample integrity and row-level errors."""
from pathlib import Path

from app.services.csv_import import parse_comparables_csv, template_csv

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample" / "comparables_sample.csv"

HEADER = ("address,city,zip_code,latitude,longitude,property_type,sale_price,"
          "sale_date,square_feet,lot_size,bedrooms,bathrooms,year_built,"
          "condition,parking_spaces,pool,distance_from_subject,notes,source")


def build_csv(*rows):
    return HEADER + "\n" + "\n".join(rows) + "\n"


GOOD_ROW = ("1 Good St,Arcadia,91006,34.14,-118.03,single_family,1000000,"
            "2026-05-01,1800,7000,3,2,1960,good,2,false,0.5,ok,synthetic-demo")


def errors_for(result, field):
    return [e for e in result[1] if e["field"] == field]


def test_template_parses_cleanly():
    rows, errors = parse_comparables_csv(template_csv())
    assert errors == []
    assert len(rows) == 1
    assert rows[0]["address"] == "1234 Example St"


def test_bundled_sample_parses_cleanly():
    rows, errors = parse_comparables_csv(SAMPLE.read_text())
    assert errors == []
    assert len(rows) == 20
    assert all(row["source"] == "synthetic-demo" for row in rows)


def test_empty_file():
    rows, errors = parse_comparables_csv("")
    assert rows == []
    assert errors[0]["field"] == "file"


def test_missing_required_column():
    text = "address,sale_price\n1 Main St,1000000\n"
    rows, errors = parse_comparables_csv(text)
    assert rows == []
    assert errors[0]["field"] == "header"
    assert "sale_date" in errors[0]["message"]


def test_row_level_errors_do_not_block_valid_rows():
    bad_price = GOOD_ROW.replace("1000000", "-5")
    rows, errors = parse_comparables_csv(build_csv(GOOD_ROW, bad_price))
    assert len(rows) == 1
    assert len(errors) == 1
    assert errors[0]["row"] == 2
    assert errors[0]["field"] == "sale_price"


def test_zero_square_feet_rejected():
    bad = GOOD_ROW.replace(",1800,", ",0,")
    result = parse_comparables_csv(build_csv(bad))
    assert result[0] == []
    assert errors_for(result, "square_feet")


def test_invalid_and_future_dates_rejected():
    bad_format = GOOD_ROW.replace("2026-05-01", "May 1 2026")
    future = GOOD_ROW.replace("2026-05-01", "2099-01-01")
    result = parse_comparables_csv(build_csv(bad_format, future))
    assert result[0] == []
    assert len(errors_for(result, "sale_date")) == 2


def test_fractional_bedrooms_rejected():
    bad = GOOD_ROW.replace(",3,2,", ",2.5,2,")
    result = parse_comparables_csv(build_csv(bad))
    assert errors_for(result, "bedrooms")


def test_unknown_condition_rejected():
    bad = GOOD_ROW.replace(",good,", ",pristine,")
    result = parse_comparables_csv(build_csv(bad))
    assert errors_for(result, "condition")


def test_invalid_pool_value_rejected():
    bad = GOOD_ROW.replace(",false,", ",maybe,")
    result = parse_comparables_csv(build_csv(bad))
    assert errors_for(result, "pool")


def test_out_of_range_coordinates_rejected():
    bad = GOOD_ROW.replace("34.14", "134.14")
    result = parse_comparables_csv(build_csv(bad))
    assert errors_for(result, "latitude")


def test_missing_address_rejected():
    bad = "," + GOOD_ROW.split(",", 1)[1]
    result = parse_comparables_csv(build_csv(bad))
    assert errors_for(result, "address")


def test_currency_formatting_accepted():
    formatted = GOOD_ROW.replace("1000000", '"$1,000,000"')
    rows, errors = parse_comparables_csv(build_csv(formatted))
    assert errors == []
    assert rows[0]["sale_price"] == 1_000_000


def test_optional_fields_may_be_blank():
    minimal_header = "address,sale_price,sale_date,square_feet,bedrooms,bathrooms"
    text = minimal_header + "\n2 Min St,900000,2026-04-01,1500,3,2\n"
    rows, errors = parse_comparables_csv(text)
    assert errors == []
    assert rows[0]["lot_size"] is None
    # Blank pool and property_type stay unknown; missing data is never guessed.
    assert rows[0]["has_pool"] is None
    assert rows[0]["property_type"] is None
