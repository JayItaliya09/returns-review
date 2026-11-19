"""Draw the README's metric and ranking chart from the published marts."""
import csv
from html import escape
from generate import ROOT


def rows(name):
    with (ROOT / f"data/mart/{name}.csv").open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def draw():
    cohorts = rows("cohorts")
    drivers = rows("opportunities")[:5]
    units, returned, erosion = (sum(int(r[k]) for r in cohorts) for k in ("shipped_units","returned_units","erosion_c"))
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 540" role="img"><title>Annual retail returns and five largest margin exposures</title>',
             '<rect width="1040" height="540" rx="18" fill="#102f38"/>']
    def label(x,y,value,size=19,color="#eaf5ed",weight=400):
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>')
    label(36,44,"OPERATIONS REVIEW     /     FY 2025",16,"#99e4cc",700)
    label(36,96,"Where returns erode margin",40,weight=700)
    for x,number,caption in [(36,f"{units:,}","Units shipped"),(360,f"{returned/units:.2%}","Unit return rate"),(690,f"€{erosion/100:,.0f}","Margin erosion")]:
        label(x,167,number,38);label(x,198,caption,17,"#abd0c6")
    parts.append('<path d="M36 223 H1004" stroke="#52716f"/>')
    label(36,261,"Largest exposures by product, channel and return reason",23,weight=700)
    maximum = int(drivers[0]["erosion_c"])
    for i,r in enumerate(drivers):
        y=301+41*i
        label(36,y,f"{r['product']}  /  {r['channel']}  /  {r['reason']}",17)
        w=390*int(r["erosion_c"])/maximum
        parts.append(f'<rect x="438" y="{y-16}" width="{w:.1f}" height="19" rx="3" fill="{("#92e8bd" if i==0 else "#58a69d")}"/>')
        label(848,y,"€"+format(int(r["erosion_c"])/100,",.2f"),18)
    label(36,512,"Simulated retailer   •   2025 shipment cohorts   •   30-day return window",15,"#abd0c6")
    (ROOT / "docs/overview.svg").write_text("\n".join(parts+["</svg>"]),encoding="utf-8")


if __name__ == "__main__":
    draw()
