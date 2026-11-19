"""Reconcile reporting components to the shipped fixed-seed portfolio snapshot."""
import base64
import csv
import json
import re
import sqlite3
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from generate import ROOT


def check(label, actual, expected):
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, saw {actual!r}")


def verify():
    mart = ROOT / "data/mart"
    with sqlite3.connect(mart / "returns.sqlite") as db:
        totals = db.execute("SELECT SUM(shipped_units), SUM(returned_units), SUM(erosion_c) FROM cohorts").fetchone()
        check("reference snapshot", totals, (17743,1784,8870995))
        top = db.execute("SELECT product,reason,events,erosion_c FROM opportunities WHERE priority=1").fetchone()
        check("priority", top, ("Trail runner","Fit",265,1418295))
    bi = ROOT / "powerbi"
    model = json.loads((bi / "Review.SemanticModel/model.bim").read_text())["model"]
    tables = {table["name"]:table for table in model["tables"]}
    for table, filename in [("Cohorts","cohorts"),("Drivers","opportunities")]:
        source = " ".join(tables[table]["partitions"][0]["source"]["expression"])
        encoded = re.search(r'Binary.FromText\("([^"]+)"',source).group(1)
        check("model snapshot",base64.b64decode(encoded),(mart/f"{filename}.csv").read_bytes())
    visuals = list(bi.rglob("visual.json"))
    check("report visuals",len(visuals),9)
    for path in visuals:
        roles = json.loads(path.read_text())["visual"]["query"]["queryState"]
        for role in roles.values():
            for projection in role["projections"]:
                kind, ref = next(iter(projection["field"].items()))
                table = tables[ref["Expression"]["SourceRef"]["Entity"]]
                valid = {v["name"] for v in table["columns" if kind=="Column" else "measures"]}
                check("visual field resolves", ref["Property"] in valid,True)
    with ZipFile(ROOT / "reports/Returns-review.xlsx") as book:
        ns = {"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        for cell, expected in [("B5",totals[0]),("B6",totals[1]),("B8",totals[2]/100),("B18",627.4425)]:
            node = sheet.find(f".//x:c[@r='{cell}']",ns)
            check("live formula "+cell,node.find("x:f",ns) is not None,True)
            check("Excel cached value "+cell,round(float(node.findtext("x:v",namespaces=ns)),4),expected)
    print("Verified SQL snapshot, both Power Query inputs, nine report visual bindings and Excel KPI formulas.")


if __name__ == "__main__":
    verify()
