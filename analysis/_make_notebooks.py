"""Builds and executes the six analysis notebooks from the cell scripts in analysis/_cells/.

    python analysis/_make_notebooks.py            # build + execute every notebook (outputs saved, charts written to docs/eda and docs/ds)
    python analysis/_make_notebooks.py --no-exec  # only (re)write the .ipynb files
    python analysis/_make_notebooks.py 02 05      # only notebooks whose number is listed

A cell script is plain Python: a line `# %%` starts a code cell, `# %% [markdown]` starts a markdown cell whose lines are written as `# text`.
Needs: nbformat, nbclient, ipykernel, seaborn, pandas, scipy, statsmodels, scikit-learn, matplotlib.
"""
import re
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent
CELLS = HERE / "_cells"
BOOKS = {
    "00_load_clean": ["00_load_clean.py"],
    "01_audit": ["01_audit.py"],
    "02_eda": ["02_eda.py"],
    "03_forecast": ["03_forecast.py"],
    "04_data_science": ["04_data_science.py"],
    "05_deep_dives": ["05a_rca.py", "05b_cohort_rfm.py", "05c_commercial.py"],
}


def parse(text):
    cells, kind, buf = [], None, []

    def flush():
        if kind is None:
            return
        body = "\n".join(buf).strip("\n")
        if not body.strip():
            return
        if kind == "md":
            body = "\n".join(re.sub(r"^# ?", "", ln) for ln in body.split("\n"))
            cells.append(nbf.v4.new_markdown_cell(body))
        else:
            cells.append(nbf.v4.new_code_cell(body))

    for ln in text.split("\n"):
        if ln.startswith("# %%"):
            flush()
            kind, buf = ("md" if "[markdown]" in ln else "code"), []
        else:
            buf.append(ln)
    flush()
    return cells


def build(name, files):
    book = nbf.v4.new_notebook()
    book.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for f in files:
        book.cells += parse((CELLS / f).read_text(encoding="utf-8"))
    return book


def main(argv):
    execute = "--no-exec" not in argv
    pick = [a for a in argv if not a.startswith("--")]
    for name, files in BOOKS.items():
        if pick and name[:2] not in pick:
            continue
        book = build(name, files)
        path = HERE / f"{name}.ipynb"
        if execute:
            print(f"executing {name} ({len(book.cells)} cells) ...", flush=True)
            NotebookClient(book, timeout=1200, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
        nbf.write(book, path)
        print("wrote", path.name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
