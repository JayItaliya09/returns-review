"""Package SQL reporting marts as embedded Power Query tables in a portable PBIP."""
import base64
import csv
import json
from pathlib import Path
from generate import ROOT

BI = ROOT / "powerbi"
REPORT = BI / "Review.Report"
MODEL = BI / "Review.SemanticModel"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def definition(path, schema, **properties):
    base = SCHEMA.replace("/item/", "/pbip/") if schema.startswith("pbipProperties") else SCHEMA
    save(path, {"$schema": base + schema + "/schema.json", **properties})


def make_table(name, filename, text_columns, metrics):
    path = ROOT / "data/mart" / filename
    with path.open(encoding="utf-8") as source:
        headers = next(csv.reader(source))
    encoded = base64.b64encode(path.read_bytes()).decode()
    conversions = ", ".join('{"%s", Int64.Type}' % col for col in headers if col not in text_columns and col != "share_pct")
    if "share_pct" in headers:
        conversions += ', {"share_pct", type number}'
    expression = [
        "let",
        f'    Source = Csv.Document(Binary.FromText("{encoded}", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001]),',
        "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        "    Typed = Table.TransformColumnTypes(Headers, {" + conversions + '}, "en-US")',
        "in Typed",
    ]
    columns = [{"name": col, "sourceColumn": col, "dataType":
                "string" if col in text_columns else "double" if col == "share_pct" else "int64"}
               for col in headers]
    return {"name":name,"columns":columns,"partitions":[{"name":name,"mode":"import",
            "source":{"type":"m","expression":expression}}],
            "measures":[{"name":label,"expression":dax,"formatString":fmt} for label,dax,fmt in metrics]}


def field(table, name, kind):
    return {"field":{kind:{"Expression":{"SourceRef":{"Entity":table}},"Property":name}},
            "queryRef":f"{table}.{name}", "nativeQueryRef":name}


def page(page_id, title, specs):
    folder = REPORT / "definition/pages" / page_id
    definition(folder / "page.json","report/definition/page/1.0.0", name=page_id,
               displayName=title,displayOption="FitToPage",height=720,width=1280)
    for index, (kind,label,xywh,roles) in enumerate(specs):
        name = f"{page_id}{index:02d}"
        query = {role:{"projections":refs} for role, refs in roles.items()}
        text = {"expr":{"Literal":{"Value":"'" + label + "'"}}}
        visual = {"visualType":kind,"query":{"queryState":query},
                  "visualContainerObjects":{"title":[{"properties":{"show":{"expr":{"Literal":{"Value":"true"}}},"text":text}}]}}
        x,y,w,h = xywh
        definition(folder / "visuals" / name / "visual.json","report/definition/visualContainer/2.0.0",
                   name=name,position=dict(x=x,y=y,width=w,height=h,z=index,tabOrder=index),visual=visual)


def build_report():
    euro, count = '€#,0.00', '#,0'
    tables = [make_table("Cohorts","cohorts.csv",{"month","category","product","channel"},[
        ("Units shipped","SUM(Cohorts[shipped_units])",count),
        ("Units returned","SUM(Cohorts[returned_units])",count),
        ("Return rate","DIVIDE([Units returned], [Units shipped])","0.00%"),
        ("Margin erosion","SUM(Cohorts[erosion_c]) / 100",euro),
        ("Refunds","SUM(Cohorts[refund_c]) / 100",euro)]),
        make_table("Drivers","opportunities.csv",{"channel","product","reason"},[
        ("Return events","SUM(Drivers[events])",count),
        ("Cost exposure","SUM(Drivers[erosion_c]) / 100",euro)])]
    save(MODEL / "model.bim",{"name":"Review","compatibilityLevel":1567,
         "model":{"culture":"en-US","defaultPowerBIDataSourceVersion":"powerBI_V3","tables":tables}})
    definition(MODEL / "definition.pbism","semanticModel/definitionProperties/1.0.0",version="1.0",settings={})
    definition(BI / "Review.pbip","pbipProperties/1.0.0",version="1.0",artifacts=[{"report":{"path":"Review.Report"}}],settings={"enableAutoRecovery":True})
    definition(REPORT / "definition.pbir","report/definitionProperties/2.0.0",version="4.0",
               datasetReference={"byPath":{"path":"../Review.SemanticModel"}})
    folder = REPORT / "definition"
    definition(folder / "version.json","report/definition/versionMetadata/1.0.0",version="2.0.0")
    definition(folder / "report.json","report/definition/report/1.0.0",themeCollection={},layoutOptimization="None")
    definition(folder / "pages/pages.json","report/definition/pagesMetadata/1.0.0",
               pageOrder=["overview","priorities"],activePageName="overview")
    def col(name, table="Cohorts"): return field(table,name,"Column")
    def measure(name, table="Cohorts"): return field(table,name,"Measure")
    cards = [("card",name,(20+i*315,15,300,135),{"Values":[measure(name)]})
             for i,name in enumerate(["Units shipped","Units returned","Return rate","Margin erosion"])]
    page("overview","Returns overview",cards + [
        ("lineChart","Return rate by shipment month",(20,175,735,500),{"Category":[col("month")],"Y":[measure("Return rate")]}),
        ("barChart","Margin erosion by category",(780,175,480,500),{"Category":[col("category")],"Y":[measure("Margin erosion")]})])
    page("priorities","Investigation priorities",[
        ("barChart","Exposure by return reason",(20,20,610,310),{"Category":[col("reason","Drivers")],"Y":[measure("Cost exposure","Drivers")]}),
        ("barChart","Exposure by sales channel",(650,20,610,310),{"Category":[col("channel","Drivers")],"Y":[measure("Cost exposure","Drivers")]}),
        ("tableEx","Product, channel and reason detail",(20,350,1240,350),{"Values":[col(c,"Drivers") for c in ("product","channel","reason")] + [measure(c,"Drivers") for c in ("Return events","Cost exposure")]})])


if __name__ == "__main__":
    build_report()
