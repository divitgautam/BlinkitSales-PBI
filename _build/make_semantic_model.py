"""Writes the BlinkitSales-PBI PBIP skeleton and semantic model (TMDL).
Run with Power BI Desktop CLOSED on this project:  python _build/make_semantic_model.py
Definitions mirror docs/reconciliation.md exactly (revenue = SUM(order_total); line value only for category mix).
Tables and columns are declared in tables_spec.py; measures in measures_spec.py."""
import json
import re
import uuid
from pathlib import Path

from tables_spec import SPEC, CALC, KEYS, CATEGORY, REL_FROM, RELS, SORT_BY
from measures_spec import MEASURES

ROOT = Path(__file__).resolve().parents[1]
NAME = "BlinkitSales-PBI"
RPT, SM = ROOT / f"{NAME}.Report", ROOT / f"{NAME}.SemanticModel"
DEFN = SM / "definition"
T = "\t"
BASE_THEME_SRC = Path(r"D:\Wolf\PBI\AirlineDataAnalysis-PBI\AirlineDataAnalysis-PBI.Report\StaticResources\SharedResources\BaseThemes")


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def platform(kind: str) -> str:
    return json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                       "metadata": {"type": kind, "displayName": NAME},
                       "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}}, indent=2)


def lt() -> str:
    return f"lineageTag: {uuid.uuid4()}"


q = lambda n: f"'{n}'" if re.search(r"[^A-Za-z0-9_]", n) else n
ind = lambda m, n: "\n".join(T * n + ln for ln in m.splitlines())
IGNORE = lambda ids: f"{T}annotation BestPracticeAnalyzer_IgnoreRules = " + json.dumps({"RuleIDs": ids}) + "\n"

# ---------------------------------------------------------------- PBIP + minimal report shell (pages come from build_report.py in Phase 4)
w(ROOT / f"{NAME}.pbip", json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                     "settings": {"enableAutoRecovery": True}}, indent=2))
w(RPT / "definition.pbir", json.dumps({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
if not (RPT / ".platform").exists():
    w(RPT / ".platform", platform("Report"))
w(RPT / "definition" / "version.json", json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2))
if not (RPT / "definition" / "report.json").exists():
    rv = {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}
    rep = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
           "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU10", "reportVersionAtImport": rv, "type": "SharedResources"}},
           "objects": {"section": [{"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}],
                       "outspacePane": [{"properties": {"expanded": {"expr": {"Literal": {"Value": "false"}}}}}]},
           "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                                 "items": [{"name": "Fluent2-CY26SU10", "path": "BaseThemes/Fluent2-CY26SU10.json", "type": "BaseTheme"}]}],
           "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                        "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}}
    w(RPT / "definition" / "report.json", json.dumps(rep, indent=2))
    for f in BASE_THEME_SRC.glob("*.json"):
        w(RPT / "StaticResources" / "SharedResources" / "BaseThemes" / f.name, f.read_text(encoding="utf-8"))
if not (RPT / "definition" / "pages" / "pages.json").exists():   # placeholder page so Desktop opens; Phase 4 replaces it
    w(RPT / "definition" / "pages" / "pages.json", json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
                                                              "pageOrder": ["overview"], "activePageName": "overview"}, indent=2))
    w(RPT / "definition" / "pages" / "overview" / "page.json", json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                                                                            "name": "overview", "displayName": "1 Overview", "displayOption": "FitToPage",
                                                                            "height": 720, "width": 1280}, indent=2))

# ---------------------------------------------------------------- semantic model skeleton
w(SM / "definition.pbism", json.dumps({"version": "4.2", "settings": {}}, indent=2))
if not (SM / ".platform").exists():
    w(SM / ".platform", platform("SemanticModel"))
w(DEFN / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n\n")
if not (DEFN / "cultures" / "en-IN.tmdl").exists():   # keep Desktop's linguistic metadata once it has written it
    w(DEFN / "cultures" / "en-IN.tmdl", "cultureInfo en-IN\n")
FACTS_DIMS = list(SPEC)
TABLES = FACTS_DIMS + ["Date", "_Measures"]
w(DEFN / "model.tmdl",
  "model Model\n\tculture: en-IN\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-IN\n"
  "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
  "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
  'annotation PBI_QueryOrder = ["ProjectFolder","SourceFolder"' + "".join(f',"{t}"' for t in FACTS_DIMS) + "]\n\n"
  'annotation PBI_ProTooling = ["DevMode"]\n\n'
  + "".join(f"ref table {q(t)}\n" for t in TABLES) + "\nref cultureInfo en-IN\n")


def param(name, value, desc):
    return (f'/// {desc}\nexpression {name} = "{value}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
            f"{T}{lt()}\n\n{T}annotation PBI_NavigationStepName = Navigation\n\n{T}annotation PBI_ResultType = Text\n\n")


w(DEFN / "expressions.tmdl",
  param("ProjectFolder", str(ROOT), "Project folder on this machine. Change it when the project moves.")
  + param("SourceFolder", "data\\clean", "Folder with the clean CSV files, relative to ProjectFolder."))

# ---------------------------------------------------------------- tables from the clean CSVs
MT = {"int64": "Int64.Type", "string": "type text", "dateTime": "type date", "decimal": "Currency.Type", "boolean": "type logical"}


def column(name, dtype, fmt, hidden, desc, key=False, category=None, mdx_off=False, sort_by=None):
    s = f"{T}/// {desc}\n{T}column {q(name)}\n{T * 2}dataType: {dtype}\n"
    if fmt: s += f"{T * 2}formatString: {fmt}\n"
    if key: s += f"{T * 2}isKey\n"
    if hidden: s += f"{T * 2}isHidden\n"
    if mdx_off: s += f"{T * 2}isAvailableInMdx: false\n"
    if category: s += f"{T * 2}dataCategory: {category}\n"
    if sort_by: s += f"{T * 2}sortByColumn: {q(sort_by)}\n"
    s += f"{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}sourceColumn: {name}\n\n{T * 2}annotation SummarizationSetBy = User\n\n"
    return s


def calc_column(name, dtype, expr, fmt, hidden, sort_by, desc):
    s = f"{T}/// {desc}\n{T}column {q(name)} = {expr}\n{T * 2}dataType: {dtype}\n"
    if fmt: s += f"{T * 2}formatString: {fmt}\n"
    if hidden: s += f"{T * 2}isHidden\n"
    if sort_by: s += f"{T * 2}sortByColumn: {q(sort_by)}\n"
    s += f"{T * 2}{lt()}\n{T * 2}summarizeBy: none\n\n{T * 2}annotation SummarizationSetBy = Automatic\n\n"
    return s


for t, (tdesc, cols) in SPEC.items():
    src_names = ", ".join(f'"{c[0]}"' for c in cols)
    types = ", ".join('{"%s", %s}' % (c[0], MT[c[2]]) for c in cols)
    ren = ", ".join('{"%s", "%s"}' % (c[0], c[1]) for c in cols)
    m = ("let\n"
         f'    Source = Csv.Document(File.Contents(ProjectFolder & "\\" & SourceFolder & "\\{t}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
         "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
         f"    Selected = Table.SelectColumns(Promoted, {{{src_names}}}),\n"
         f'    Typed = Table.TransformColumnTypes(Selected, {{{types}}}, "en-US"),\n'
         f"    Renamed = Table.RenameColumns(Typed, {{{ren}}})\n"
         "in\n    Renamed")
    s = f"/// {tdesc}\ntable {t}\n{T}{lt()}\n\n"
    for src, nm, dt, fmt, hid, desc in cols:
        mdx_off = hid and (t, nm) not in REL_FROM and (t, nm) not in KEYS and nm not in {v for (tt, _), v in SORT_BY.items() if tt == t}
        s += column(nm, dt, fmt, hid, desc, key=(t, nm) in KEYS, category=CATEGORY.get((t, nm)), mdx_off=mdx_off, sort_by=SORT_BY.get((t, nm)))
    for nm, dt, expr, fmt, hid, sb, desc in CALC.get(t, []):
        s += calc_column(nm, dt, expr, fmt, hid, sb, desc)
    s += f"{T}partition {t} = m\n{T * 2}mode: import\n{T * 2}source =\n{ind(m, 4)}\n\n{T}annotation PBI_ResultType = Table\n"
    # table names keep the fact_/dim_ convention the project spec asks for (lowercase): documented BPA exception
    s += "\n" + IGNORE(["FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED"])
    w(DEFN / "tables" / f"{t}.tmdl", s)

# ---------------------------------------------------------------- Date (calculated: whole months over orders, marketing and inventory)
date_dax = ('VAR lo = MIN ( MIN ( MIN ( fact_orders[Order Date] ), MIN ( fact_marketing[Campaign Date] ) ), MIN ( fact_inventory[Month Start] ) ) '
            'VAR hi = MAX ( MAX ( MAX ( fact_orders[Order Date] ), MAX ( fact_marketing[Campaign Date] ) ), MAX ( fact_inventory[Month Start] ) ) '
            'VAR firstMonth = DATE ( YEAR ( MIN ( fact_orders[Order Date] ) ), MONTH ( MIN ( fact_orders[Order Date] ) ), 1 ) '
            'VAR lastMonth = DATE ( YEAR ( MAX ( fact_orders[Order Date] ) ), MONTH ( MAX ( fact_orders[Order Date] ) ), 1 ) '
            'RETURN ADDCOLUMNS ( CALENDAR ( DATE ( YEAR ( lo ), MONTH ( lo ), 1 ), EOMONTH ( hi, 0 ) ), '
            '"Year", YEAR ( [Date] ), "Quarter", "Q" & QUARTER ( [Date] ), "Month No", MONTH ( [Date] ), '
            '"Month", FORMAT ( [Date], "MMM", "en-US" ), "Month Start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ), '
            '"Year Month", FORMAT ( [Date], "MMM yy", "en-US" ), "Year Month Key", YEAR ( [Date] ) * 100 + MONTH ( [Date] ), '
            '"Weekday No", WEEKDAY ( [Date], 2 ), "Weekday", FORMAT ( [Date], "ddd", "en-US" ), '
            '"Is Full Month", NOT ( DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ) = firstMonth || DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ) = lastMonth ) )')
dcols = [("Date", "dateTime", "dd-mmm-yyyy", None, "Calendar date (key)."), ("Year", "int64", "0", None, "Calendar year."),
         ("Quarter", "string", None, None, "Calendar quarter, Q1-Q4."), ("Month No", "int64", "0", None, "Month number, 1-12 (sorts Month)."),
         ("Month", "string", None, "Month No", "Month name, e.g. Jan."), ("Month Start", "dateTime", "mmm yyyy", None, "First day of the month."),
         ("Year Month", "string", None, "Year Month Key", "Month label, e.g. Mar 24."), ("Year Month Key", "int64", "0", None, "yyyymm number (sorts Year Month)."),
         ("Weekday No", "int64", "0", None, "Weekday number, Monday = 1 (sorts Weekday)."), ("Weekday", "string", None, "Weekday No", "Weekday name, e.g. Mon."),
         ("Is Full Month", "boolean", None, None, "FALSE for the first and last month of the order data (Mar 2023 and Nov 2024), which are partial; exclude them from trends and YoY.")]
ds = (f"/// Calendar of whole months from Mar 2023 to Nov 2024, shared by orders, marketing and inventory; marked as the date table.\n"
      f"table Date\n{T}{lt()}\n{T}dataCategory: Time\n\n")
for n, d, f, sb, desc in dcols:
    s = f"{T}/// {desc}\n{T}column {q(n)}\n{T * 2}dataType: {d}\n"
    if n == "Date": s += f"{T * 2}isKey\n"
    if f: s += f"{T * 2}formatString: {f}\n"
    if sb: s += f"{T * 2}sortByColumn: {q(sb)}\n"
    s += f"{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}isNameInferred\n{T * 2}sourceColumn: [{n}]\n\n"
    ds += s
ds += f"{T}partition Date = calculated\n{T * 2}mode: import\n{T * 2}source = {date_dax}\n"
w(DEFN / "tables" / "Date.tmdl", ds)

# ---------------------------------------------------------------- Measures table
ms = f"/// Central home for report measures (no data).\ntable _Measures\n{T}{lt()}\n\n"
for n, e, fmt, folder, desc in MEASURES:
    ms += f"{T}/// {desc}\n{T}measure {q(n)} = {e}\n"
    if fmt: ms += f"{T * 2}formatString: {fmt}\n"
    ms += f"{T * 2}displayFolder: {folder}\n{T * 2}{lt()}\n\n"
ms += (f"{T}column Hidden\n{T * 2}dataType: string\n{T * 2}isHidden\n{T * 2}isAvailableInMdx: false\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}isNameInferred\n{T * 2}sourceColumn: [Hidden]\n\n"
       f"{T}partition _Measures = calculated\n{T * 2}mode: import\n{T * 2}source = ROW ( \"Hidden\", BLANK () )\n\n"
       + IGNORE(["ENSURE_TABLES_HAVE_RELATIONSHIPS", "REMOVE_UNNECESSARY_COLUMNS"]))
w(DEFN / "tables" / "_Measures.tmdl", ms)

# ---------------------------------------------------------------- relationships: star schema, many-to-one, single direction (TMDL defaults)
w(DEFN / "relationships.tmdl", "\n".join(f"relationship {n}\n\tfromColumn: {a}\n\ttoColumn: {b}\n" for n, a, b in RELS))
print(f"model written: {len(TABLES)} tables, {len(MEASURES)} measures, {len(RELS)} relationships")
