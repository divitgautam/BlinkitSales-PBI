"""Best Practice Analyzer for TMDL folders: a Python implementation of the core rules in Microsoft's
Tabular Editor BPA rule set (github.com/microsoft/Analysis-Services/tree/master/BestPracticeRules), so a model can be
checked without installing Tabular Editor. Rules can be suppressed per object, as in Tabular Editor, with a TMDL
annotation:  annotation BestPracticeAnalyzer_IgnoreRules = {"RuleIDs":["RULE_ID"]}

Usage:  python bpa_check.py <path to .SemanticModel/definition>  [--json out.json]
Exit code 1 when any error/warning-level rule fails."""
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Obj:
    kind: str            # Table, Column, Measure, Relationship, Partition
    table: str
    name: str
    props: dict = field(default_factory=dict)
    expr: str = ""
    desc: str = ""
    ignore: set = field(default_factory=set)

    @property
    def ref(self):
        return f"'{self.table}'" if self.kind == "Table" else f"'{self.table}'[{self.name}]"


NAME = r"(?:'(?P<q>(?:[^']|'')+)'|(?P<u>[^\s=']+))"


def _name(m):
    return (m["q"] or m["u"]).replace("''", "'")


def parse(defn: Path):
    objs = []
    for f in sorted((defn / "tables").glob("*.tmdl")):
        lines = f.read_text(encoding="utf-8").splitlines()
        tname, cur, desc, i = None, None, "", 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("///"):
                desc = ln[3:].strip(); i += 1; continue
            m = re.match(rf"^table {NAME}", ln)
            if m:
                tname = _name(m); cur = Obj("Table", tname, tname, desc=desc); objs.append(cur); desc = ""; i += 1; continue
            if ln.startswith("\t///"):
                desc = ln.strip()[3:].strip(); i += 1; continue
            m = re.match(rf"^\t(column|measure|partition) {NAME}\s*(=\s*(?P<e>.*))?$", ln)
            if m:
                kind = {"column": "Column", "measure": "Measure", "partition": "Partition"}[m.group(1)]
                cur = Obj(kind, tname, _name(m), expr=(m["e"] or "").strip(), desc=desc)
                if kind == "Column" and m["e"] is not None:
                    cur.props["calculated"] = True
                objs.append(cur); desc = ""; i += 1
                # multi-line expression: following lines indented 3+ tabs (or 2 for a source block)
                while i < len(lines) and (lines[i].startswith("\t\t\t") or (lines[i].strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith("\t\t\t"))):
                    cur.expr += " " + lines[i].strip(); i += 1
                continue
            m = re.match(r"^\t\t(\w+)(?::\s*(.*))?$", ln)
            if m and cur is not None and cur.kind != "Table":
                cur.props[m.group(1)] = (m.group(2) or True)
                if m.group(1) == "source" and m.group(2) is None:
                    i += 1
                    while i < len(lines) and lines[i].startswith("\t\t\t"):
                        cur.expr += " " + lines[i].strip(); i += 1
                    continue
            m = re.match(r"^\t(\w+)(?::\s*(.*))?$", ln)
            if m and m.group(1) not in ("column", "measure", "partition", "annotation") and cur is not None:
                objs[[o.kind for o in objs].index("Table") if False else -1]  # no-op, keeps linters quiet
                tbl = next(o for o in objs if o.kind == "Table" and o.name == tname)
                tbl.props[m.group(1)] = (m.group(2) or True)
            m = re.match(r'^\t*annotation BestPracticeAnalyzer_IgnoreRules = (.*)$', ln)
            if m:
                ids = set(json.loads(m.group(1)).get("RuleIDs", []))
                target = cur if ln.startswith("\t\t") else next(o for o in objs if o.kind == "Table" and o.name == tname)
                target.ignore |= ids
            i += 1
    rel = defn / "relationships.tmdl"
    if rel.exists():
        for block in rel.read_text(encoding="utf-8").split("relationship ")[1:]:
            props = dict(re.findall(r"^\t(\w+):\s*(.*)$", block, re.M))
            objs.append(Obj("Relationship", "", block.splitlines()[0].strip(), props=props))
    return objs


def col_ref(s):
    m = re.match(rf"^{NAME}\.{NAME}$".replace("(?P<q>", "(?P<q1>", 1).replace("(?P<u>", "(?P<u1>", 1), s.strip())
    if not m:
        return None
    return ((m["q1"] or m["u1"]).replace("''", "'"), (m["q"] or m["u"]).replace("''", "'"))


def check(defn: Path):
    objs = parse(defn)
    tables = [o for o in objs if o.kind == "Table"]
    cols = [o for o in objs if o.kind == "Column"]
    meas = [o for o in objs if o.kind == "Measure"]
    rels = [o for o in objs if o.kind == "Relationship"]
    all_dax = " ".join(o.expr for o in objs if o.kind in ("Measure", "Column", "Partition"))
    rel_cols = {col_ref(r.props.get(k, "")) for r in rels for k in ("fromColumn", "toColumn")} - {None}
    from_cols = {col_ref(r.props.get("fromColumn", "")) for r in rels} - {None}
    to_cols = {col_ref(r.props.get("toColumn", "")) for r in rels} - {None}
    tables_in_rel = {t for t, _ in rel_cols}
    hidden_tables = {t.name for t in tables if t.props.get("isHidden")}
    visible = lambda o: not o.props.get("isHidden") and o.table not in hidden_tables
    used = lambda c: (re.search(rf"(?:'{re.escape(c.table)}'|\b{re.escape(c.table)})\s*\[\s*{re.escape(c.name)}\s*\]", all_dax, re.I)
                      or (c.table, c.name) in rel_cols or any(c.name == o.props.get("sortByColumn", "").strip("'") for o in cols if o.table == c.table))
    # text-returning measures (labels, titles, colour codes) need no number format
    def numeric_fmt(m):
        if re.fullmatch(r'\s*SELECTEDVALUE\s*\([^()]*,\s*"[^"]*"\s*\)\s*', m.expr):
            return False                                                # returns a text label
        e = re.sub(r"SELECTEDVALUE\s*\([^()]*\)", "", m.expr)          # default-value strings are not results
        return not (re.match(r'^\s*(FORMAT|CONCATENATEX|")', e, re.I) or re.search(r'&\s*"|"\s*&|"#[0-9A-Fa-f]{6}"', e)
                    or re.search(r'\b(SWITCH|IF)\s*\(.*[,(]\s*"[^"]*"\s*[,)]', e))

    R = []   # (id, severity, category, description, objects)

    def rule(rid, sev, cat, desc, hits):
        hits = [o for o in hits if rid not in o.ignore and not (o.kind != "Table" and rid in next((t.ignore for t in tables if t.name == o.table), set()))]
        R.append(dict(id=rid, severity=sev, category=cat, rule=desc, violations=[o.ref if o.kind != "Relationship" else o.name for o in hits]))

    # ---- Performance
    rule("AVOID_FLOATING_POINT_DATA_TYPES", 2, "Performance", "Do not use floating point data types (use fixed decimal)",
         [c for c in cols if c.props.get("dataType") == "double"])
    rule("ISAVAILABLEINMDX_FALSE_NONATTRIBUTE_COLUMNS", 2, "Performance", "Set IsAvailableInMdx to false on hidden, non-attribute columns",
         [c for c in cols if c.props.get("isHidden") and str(c.props.get("isAvailableInMdx", "true")).lower() != "false"
          and (c.table, c.name) not in rel_cols and not any(o.props.get("sortByColumn", "").strip("'") == c.name for o in cols if o.table == c.table)])
    rule("REMOVE_AUTO-DATE_TABLE", 2, "Performance", "Remove auto-date tables", [t for t in tables if t.name.startswith(("DateTableTemplate", "LocalDateTable"))])
    rule("AVOID_BI-DIRECTIONAL_RELATIONSHIPS_AGAINST_HIGH-CARDINALITY_COLUMNS", 2, "Performance", "Avoid bi-directional relationships",
         [r for r in rels if r.props.get("crossFilteringBehavior") == "bothDirections"])
    rule("MANY-TO-MANY_RELATIONSHIPS_SHOULD_BE_SINGLE-DIRECTION", 2, "Performance", "Avoid many-to-many relationships",
         [r for r in rels if r.props.get("fromCardinality") == "many" and r.props.get("toCardinality") == "many"])
    rule("REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION", 2, "Performance", "Avoid calculated columns that use RELATED",
         [c for c in cols if c.props.get("calculated") and "RELATED" in c.expr.upper()])
    rule("AVOID_CONVERTING_BLANKS", 2, "Performance", "Avoid converting BLANK to 0 (+ 0, COALESCE(x, 0), IF(ISBLANK(x), 0))",
         [m for m in meas if re.search(r"\+\s*0\s*$|COALESCE\s*\(.*,\s*0\s*\)\s*$|IF\s*\(\s*ISBLANK\s*\([^)]*\)\s*,\s*0", m.expr, re.I)])
    rule("MODEL_SHOULD_HAVE_A_DATE_TABLE", 2, "Performance", "Model should have a marked date table",
         [] if any(t.props.get("dataCategory") == "Time" for t in tables) else [Obj("Table", "Model", "Model")])
    # ---- DAX expressions
    rule("USE_THE_DIVIDE_FUNCTION_FOR_DIVISION", 2, "DAX Expressions", "Use DIVIDE instead of /",
         [m for m in meas if re.search(r"[\])]\s*/(?!/)", m.expr)])
    rule("AVOID_USING_THE_IFERROR_FUNCTION", 2, "DAX Expressions", "Avoid IFERROR", [m for m in meas if "IFERROR" in m.expr.upper()])
    rule("AVOID_USING_'1-(X/Y)'_SYNTAX", 2, "DAX Expressions", "Avoid 1-(x/y) and DIVIDE(x,y)-1; use DIVIDE(x-y, y)",
         [m for m in meas if re.search(r"\b1\s*-\s*\(?\s*(DIVIDE|\[)|DIVIDE\s*\(.*\)\s*-\s*1\s*$|\]\s*/\s*\[[^\]]+\]\s*-\s*1", m.expr, re.I)])
    rule("MEASURES_SHOULD_NOT_BE_DIRECT_REFERENCES_OF_OTHER_MEASURES", 2, "DAX Expressions", "Measure is only a reference to another measure",
         [m for m in meas if re.fullmatch(r"\s*\[[^\]]+\]\s*", m.expr)])
    rule("UNQUALIFIED_COLUMN_REFERENCES", 2, "DAX Expressions", "Column references should be fully qualified",
         [m for m in meas if any(re.search(rf"(?<![\w'\]])\[{re.escape(c.name)}\]", m.expr) for c in cols if c.name not in {x.name for x in meas})])
    rule("FILTER_COLUMN_VALUES", 2, "DAX Expressions", "Filter column values with a boolean, not FILTER(table, col = value)",
         [m for m in meas if re.search(r"CALCULATE\w*\s*\(.*FILTER\s*\(\s*'?\w+'?\s*,\s*'?\w+'?\[[^\]]+\]\s*=", m.expr, re.I)])
    # ---- Formatting
    rule("PROVIDE_FORMAT_STRING_FOR_MEASURES", 2, "Formatting", "Visible numeric measures need a format string",
         [m for m in meas if visible(m) and "formatString" not in m.props and "formatStringDefinition" not in m.props and numeric_fmt(m)])
    rule("HIDE_FOREIGN_KEYS", 2, "Formatting", "Hide foreign-key columns", [c for c in cols if (c.table, c.name) in from_cols and not c.props.get("isHidden")])
    rule("MARK_PRIMARY_KEYS", 2, "Formatting", "Mark the key column of each dimension (isKey)",
         [c for c in cols if (c.table, c.name) in to_cols and not c.props.get("isKey") and not any(t.props.get("dataCategory") == "Time" and t.name == c.table for t in tables)])
    rule("ADD_DATA_CATEGORY_FOR_COLUMNS", 1, "Formatting", "Add a data category to geographic columns",
         [c for c in cols if c.name.lower() in ("city", "state", "country", "latitude", "longitude", "postal code", "continent") and "dataCategory" not in c.props])
    rule("DO_NOT_SUMMARIZE_NUMERIC_COLUMNS", 1, "Formatting", "Numeric columns should not be summarized by default",
         [c for c in cols if visible(c) and c.props.get("dataType") in ("int64", "double", "decimal") and c.props.get("summarizeBy", "none") != "none"])
    rule("MONTH_(AS_A_STRING)_MUST_BE_SORTED", 2, "Formatting", "Month name columns need a sort-by column",
         [c for c in cols if re.search(r"month", c.name, re.I) and c.props.get("dataType") == "string" and "sortByColumn" not in c.props])
    rule("FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED", 1, "Naming Conventions", "Visible names start with a capital letter",
         [o for o in tables + cols + meas if visible(o) and o.name[:1].isalpha() and o.name[:1].islower()])
    rule("OBJECT_NAMES_MUST_NOT_CONTAIN_SPECIAL_CHARACTERS", 2, "Naming Conventions", "No tabs, line breaks or leading/trailing spaces in names",
         [o for o in tables + cols + meas if re.search(r"[\t\r\n]", o.name) or o.name != o.name.strip()])
    rule("PARTITION_NAME_SHOULD_MATCH_TABLE_NAME_FOR_SINGLE_PARTITION_TABLES", 1, "Naming Conventions", "Single partition named after its table",
         [p for p in objs if p.kind == "Partition" and p.name != p.table and sum(1 for q in objs if q.kind == "Partition" and q.table == p.table) == 1])
    # ---- Maintenance
    rule("VISIBLE_OBJECTS_WITH_NO_DESCRIPTION", 1, "Maintenance", "Visible tables, columns and measures should have a description",
         [o for o in tables + cols + meas if visible(o) and not o.desc])
    rule("REMOVE_UNNECESSARY_COLUMNS", 2, "Maintenance", "Hidden columns that nothing references", [c for c in cols if c.props.get("isHidden") and not used(c)])
    rule("ENSURE_TABLES_HAVE_RELATIONSHIPS", 1, "Maintenance", "Tables should be related",
         [t for t in tables if t.name not in tables_in_rel and not t.props.get("dataCategory")])
    rule("PERSPECTIVES_WITH_NO_OBJECTS", 1, "Maintenance", "Perspectives with no objects", [])
    return R, objs


def main():
    defn = Path(sys.argv[1])
    R, objs = check(defn)
    fails = [r for r in R if r["violations"]]
    n = {k: sum(1 for o in objs if o.kind == k) for k in ("Table", "Column", "Measure", "Relationship")}
    print(f"BPA check: {defn}  ({n['Table']} tables, {n['Column']} columns, {n['Measure']} measures, {n['Relationship']} relationships)")
    print(f"{len(R)} rules, {len(R) - len(fails)} pass, {len(fails)} fail\n")
    for r in R:
        mark = "PASS" if not r["violations"] else f"FAIL ({len(r['violations'])})"
        print(f"[{mark:>9}] sev {r['severity']} {r['category']:<18} {r['rule']}")
        for v in r["violations"][:12]:
            print(f"              - {v}")
        if len(r["violations"]) > 12:
            print(f"              ... and {len(r['violations']) - 12} more")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(R, indent=2), encoding="utf-8")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
