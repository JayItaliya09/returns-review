import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
import fs from 'node:fs/promises';
const book = Workbook.create();
const review = book.worksheets.add("Decision");
const drivers = book.worksheets.add("Drivers");
const cohorts = book.worksheets.add("Cohorts");
const navy="#17364B", teal="#087E77", cream="#ECF6F3";
function cell(sheet, address, value) {sheet.getRange(address).values=[[value]];}
function formula(sheet, address, value) {sheet.getRange(address).formulas=[[value]];}
function band(sheet, address, color=navy) {
  const r=sheet.getRange(address); r.format.fill=color; r.format.font.color="#FFFFFF"; r.format.font.bold=true;
}
function title(sheet,address,label) {
  const r=sheet.getRange(address); r.merge(); r.values=[[label]];band(sheet,address);r.format.font.size=17;r.format.rowHeight=34;
}
async function load(sheet,name,widths){
  const raw=await fs.readFile("data/mart/"+name+".csv","utf8");
  const rows=raw.trim().split(/\r?\n/).map(line=>line.split(",").map(v=>/^[0-9]+(\.[0-9]+)?$/.test(v)?Number(v):v));
  const last=String.fromCharCode(64+rows[0].length);
  sheet.getRange("A1:"+last+rows.length).values=rows;
  sheet.tables.add("A1:"+last+rows.length,true).name=name+"Data";
  for(let i=0;i<widths.length;i++){const letter=String.fromCharCode(65+i);sheet.getRange(letter+"1").format.columnWidth=widths[i];}
  sheet.freezePanes.freezeRows(1);band(sheet,"A1:"+last+"1");
  return rows.length;
}
const d=await load(drivers,"opportunities",[11,22,14,23,13,17,15]);
const n=await load(cohorts,"cohorts",[15,19,23,14,18,18,18,21,18]);
review.showGridLines=false;
review.getRange("A1:A26").format.columnWidth=41;review.getRange("B1:B26").format.columnWidth=23;review.getRange("C1:C26").format.columnWidth=63;
title(review,"A1:C1","Returns review   /   FY 2025");
review.getRange("A2:C2").merge();cell(review,"A2","Decision workbook   •   Germany   /   EUR   •   simulated retail operations");
review.getRange("A4:C4").values=[["Portfolio performance","FY 2025","How to read it"]];band(review,"A4:C4",teal);
const labels=["Units shipped","Units returned","Unit return rate","Margin erosion"];
const forms=["=SUM(Cohorts!E2:E"+n+")","=SUM(Cohorts!F2:F"+n+")","=B6/B5","=SUM(Cohorts!I2:I"+n+")/100"];
const notes=["All shipment months, both channels","One accepted return event per unit","Weighted by units shipped","Refund less recovered inventory cost, plus return handling"];
for(let i=0;i<4;i++){cell(review,"A"+(i+5),labels[i]);formula(review,"B"+(i+5),forms[i]);cell(review,"C"+(i+5),notes[i]);}
review.getRange("A10:C10").values=[["Pilot economics","Scenario","Interpretation"]];band(review,"A10:C10",teal);
const items=[
["Target product","=INDEX(Drivers!B2:B"+d+",MATCH(1,Drivers!A2:A"+d+",0))","Highest exposure in the published ranking"],
["Channel","=INDEX(Drivers!C2:C"+d+",MATCH(1,Drivers!A2:A"+d+",0))","Pilot only on this channel"],
["Return reason","=INDEX(Drivers!D2:D"+d+",MATCH(1,Drivers!A2:A"+d+",0))","Validate reason coding before launch"],
["Baseline annual exposure","=INDEX(Drivers!F2:F"+d+",MATCH(1,Drivers!A2:A"+d+",0))/100","Observed cost across the target group"],
["Reduction assumption",0.15,"Editable • share of target exposure avoided"],
["Annual pilot cost",1500,"Editable • include content, engineering and recurring work"],
["Gross annual benefit","=B14*B15","Assumes the prevented returns have average group cost"],
["Net annual benefit","=B17-B16","Gross benefit less annual pilot cost"],
["Break-even reduction","=IFERROR(B16/B14,0)","Compare with the pilot’s measured relative reduction"]];
for(let i=0;i<items.length;i++){const [a,b,c]=items[i];const row=i+11;cell(review,"A"+row,a);if(typeof b==="string")formula(review,"B"+row,b);else cell(review,"B"+row,b);cell(review,"C"+row,c);}
for(const r of ["B8","B14","B16:B18"]) review.getRange(r).setNumberFormat('€#,##0.00');
for(const r of ["B7","B15","B19"])review.getRange(r).setNumberFormat("0.00%");
review.getRange("B5:B6").setNumberFormat("#,##0");
review.getRange("B15:B16").format.fill="#FFF0BE";review.getRange("A18:C18").format.fill=cream;review.getRange("A18:C18").format.font.bold=true;
review.getRange("A21:C21").merge();cell(review,"A21","Pilot guardrails   /   conversion rate, exchanges and contribution per visitor");
await (await SpreadsheetFile.exportXlsx(book)).save("reports/Returns-review.xlsx");
console.log(JSON.stringify(review.getRange("B14:B19").values));
