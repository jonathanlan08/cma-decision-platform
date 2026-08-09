# Sample data

**Everything in this directory is synthetic.** Addresses are fabricated
(`Demo`, `Sample`, `Example`, `Mock`, `Placeholder`, `Fictional` street names),
prices and property attributes were invented for demonstration, and no row
corresponds to a real sale, a real listing, or any client record. Coordinates
point to the general San Gabriel Valley area only so distance math has
something to work with.

| File | Purpose |
|---|---|
| `comparables_template.csv` | Blank template (header + one illustrative row) for your own data. Also downloadable from the app at `/api/csv-template`. |
| `comparables_sample.csv` | 20 synthetic comparables used by the demo seed and the e2e tests. |

## Column reference

`address` (required) · `city` · `zip_code` · `latitude` (−90..90) · `longitude`
(−180..180) · `property_type` (single_family, condo, townhouse, multi_family,
manufactured, other) · `sale_price` (required, > 0) · `sale_date` (required,
YYYY-MM-DD, not in the future) · `square_feet` (required, > 0) · `lot_size` ·
`bedrooms` (required, integer ≥ 0) · `bathrooms` (required, ≥ 0) · `year_built`
(1800–next year) · `condition` (poor, fair, average, good, excellent) ·
`parking_spaces` · `pool` (true/false) · `distance_from_subject` (miles; used
when coordinates are absent) · `notes` · `source`

Rows that fail validation are rejected individually with row/field-level error
messages; valid rows still import.
