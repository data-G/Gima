import fs from "node:fs/promises";
import path from "node:path";
import { PDFDocument } from "pdf-lib";
import sharp from "sharp";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = process.argv[2];
if (!inputPath) throw new Error("Usage: build_catering_workbook.mjs MODEL.json");
const model = JSON.parse(await fs.readFile(inputPath, "utf8"));
const outputDir = path.dirname(inputPath);
const stem = model.stem;

const wb = Workbook.create();
const summary = wb.worksheets.add("Summary");
const budget = wb.worksheets.add("Budget Detail");
const assumptions = wb.worksheets.add("Assumptions");
const sources = wb.worksheets.add("Sources");
const navy = "#17324D", teal = "#0F766E", pale = "#EAF2F8", white = "#FFFFFF", border = "#CBD5E1";
const money = '"Rs "#,##0';

function title(sheet, endCol, text, subtitle) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange(`A1:${endCol}1`).values = [[text]];
  sheet.getRange(`A1:${endCol}1`).format = { fill: navy, font: { bold: true, color: white, size: 18 }, verticalAlignment: "center" };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 34;
  sheet.getRange(`A2:${endCol}2`).merge();
  sheet.getRange(`A2:${endCol}2`).values = [[subtitle]];
  sheet.getRange(`A2:${endCol}2`).format = { fill: pale, font: { italic: true, color: navy }, wrapText: true };
  sheet.getRange(`A2:${endCol}2`).format.rowHeight = 28;
}
function header(range) {
  range.format = { fill: teal, font: { bold: true, color: white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "all", style: "thin", color: border } };
  range.format.rowHeight = 28;
}
function grid(range) { range.format = { wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: border } }; }

title(assumptions, "D", `${model.name} - Assumptions`, "Blue values are editable planning assumptions; confirm supplier quotes and production yields before purchase.");
assumptions.getRange("A4:D4").values = [["Assumption", "Value", "Unit", "Note"]]; header(assumptions.getRange("A4:D4"));
assumptions.getRange(`A5:D${4 + model.assumptions.length}`).values = model.assumptions.map(x => [x.name, x.value, x.unit, x.note]);
grid(assumptions.getRange(`A5:D${4 + model.assumptions.length}`));
assumptions.getRange(`B5:B${4 + model.assumptions.length}`).format.font = { color: "#0000FF" };
assumptions.getRange("A:A").format.columnWidth = 31; assumptions.getRange("B:B").format.columnWidth = 16; assumptions.getRange("C:C").format.columnWidth = 15; assumptions.getRange("D:D").format.columnWidth = 55;

title(budget, "J", `${model.name} - Detailed Costing`, "Quantities include line-specific waste or spare allowances. Costs are formulas, not hardcoded totals.");
budget.getRange("A4:J4").values = [["Category", "Item", "Base qty", "Waste/spare", "Buy qty", "Unit", "Unit price", "Source", "Budget cost", "Status"]]; header(budget.getRange("A4:J4"));
const start = 5, end = start + model.items.length - 1;
budget.getRange(`A${start}:H${end}`).values = model.items.map(x => [x.category, x.item, x.base_qty, x.waste, x.procure_qty, x.unit, x.unit_price, x.source]);
budget.getRange(`J${start}:J${end}`).values = model.items.map(x => [x.status]);
budget.getRange(`I${start}:I${end}`).formulas = model.items.map((_, i) => [`=E${start + i}*G${start + i}`]);
grid(budget.getRange(`A${start}:J${end}`));
budget.getRange(`D${start}:D${end}`).setNumberFormat("0.0%"); budget.getRange(`G${start}:I${end}`).setNumberFormat(money);
budget.getRange(`G${start}:G${end}`).format.font = { color: "#0000FF" }; budget.getRange(`H${start}:H${end}`).format.font = { color: "#008000" };
budget.getRange(`A${end+2}:H${end+2}`).merge(); budget.getRange(`A${end+2}:H${end+2}`).values = [["Subtotal"]]; budget.getRange(`I${end+2}`).formulas = [[`=SUM(I${start}:I${end})`]];
budget.getRange(`A${end+3}:H${end+3}`).merge(); budget.getRange(`A${end+3}:H${end+3}`).values = [[`Contingency (${(model.contingency*100).toFixed(1)}%)`]]; budget.getRange(`I${end+3}`).formulas = [[`=I${end+2}*${model.contingency}`]];
budget.getRange(`A${end+4}:H${end+4}`).merge(); budget.getRange(`A${end+4}:H${end+4}`).values = [["TOTAL BUDGET"]]; budget.getRange(`I${end+4}`).formulas = [[`=I${end+2}+I${end+3}`]];
budget.getRange(`A${end+2}:I${end+4}`).format = { fill: pale, font: { bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border } };
budget.getRange(`A${end+4}:I${end+4}`).format = { fill: navy, font: { bold: true, color: white }, borders: { preset: "all", style: "medium", color: navy } };
budget.getRange(`I${end+2}:I${end+4}`).setNumberFormat(money);
[15,25,14,14,14,12,14,13,17,20].forEach((w,i)=>budget.getRangeByIndexes(0,i,end+4,1).format.columnWidth=w);
budget.freezePanes.freezeRows(4);

title(sources, "F", "Source Register", "Official sources and retailer quotes are dated; planning estimates are explicitly marked for replacement.");
sources.getRange("A4:F4").values = [["ID", "Item", "Price", "Unit", "Source", "Caveat"]]; header(sources.getRange("A4:F4"));
sources.getRange(`A5:F${4+model.sources.length}`).values = model.sources.map(x => [x.id, x.item, x.price, x.unit, x.url, x.caveat]);
grid(sources.getRange(`A5:F${4+model.sources.length}`)); sources.getRange(`C5:C${4+model.sources.length}`).setNumberFormat(money); sources.getRange(`E5:E${4+model.sources.length}`).format.font = { color: "#008000" };
[9,31,14,13,62,45].forEach((w,i)=>sources.getRangeByIndexes(0,i,4+model.sources.length,1).format.columnWidth=w);

title(summary, "H", model.name, `${model.quantity.toLocaleString()} individually packed sandwiches | researched planning estimate | generated ${model.as_of}`);
summary.getRange("A4:B4").values = [["Key metric", "Base case"]]; header(summary.getRange("A4:B4"));
summary.getRange("A5:A9").values = [["Sandwiches"],["Subtotal"],["Contingency"],["Total budget"],["Cost per sandwich"]];
summary.getRange("B5").values = [[model.quantity]]; summary.getRange("B6").formulas = [[`='Budget Detail'!I${end+2}`]]; summary.getRange("B7").formulas = [[`='Budget Detail'!I${end+3}`]]; summary.getRange("B8").formulas = [[`='Budget Detail'!I${end+4}`]]; summary.getRange("B9").formulas = [["=B8/B5"]];
grid(summary.getRange("A5:B9")); summary.getRange("B6:B9").setNumberFormat(money); summary.getRange("B5:B9").format.font = { bold: true, color: navy, size: 12 };
summary.getRange("D4:E4").values = [["Cost category", "Budget cost"]]; header(summary.getRange("D4:E4"));
const categories = [...new Set(model.items.map(x=>x.category))];
summary.getRange(`D5:D${4+categories.length}`).values = categories.map(x=>[x]); summary.getRange(`E5:E${4+categories.length}`).formulas = categories.map((_,i)=>[`=SUMIF('Budget Detail'!$A$${start}:$A$${end},D${5+i},'Budget Detail'!$I$${start}:$I$${end})`]);
grid(summary.getRange(`D5:E${4+categories.length}`)); summary.getRange(`E5:E${4+categories.length}`).setNumberFormat(money);
const chart = summary.charts.add("bar", summary.getRange(`D4:E${4+categories.length}`)); chart.title="Cost by Category"; chart.hasLegend=false; chart.yAxis={numberFormatCode:money}; chart.setPosition("D11","H20");
summary.getRange("A12:B12").merge(); summary.getRange("A12:B12").values = [["Procurement warnings"]]; summary.getRange("A12:B12").format = { fill: teal, font:{bold:true,color:white} };
summary.getRange("A13:B17").merge(true); summary.getRange("A13:B17").values = model.warnings.slice(0,5).map(x=>[x]); summary.getRange("A13:B17").format = { fill:"#FFF7E6", font:{color:navy}, wrapText:true, borders:{preset:"all",style:"thin",color:"#D99A2B"} };
summary.getRange("A:A").format.columnWidth=27; summary.getRange("B:B").format.columnWidth=19; summary.getRange("C:C").format.columnWidth=3; summary.getRange("D:D").format.columnWidth=24; summary.getRange("E:E").format.columnWidth=18; summary.getRange("F:H").format.columnWidth=14;

const check = await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"formula scan"});
if (!check.ndjson.includes("matched 0") && !check.ndjson.includes("Cell search matched 0")) await fs.writeFile(path.join(outputDir,"formula_scan.ndjson"),check.ndjson);
const preview = await wb.render({sheetName:"Summary",range:"A1:H20",scale:1.5,format:"png"});
const png = new Uint8Array(await preview.arrayBuffer());
await sharp(png).jpeg({quality:94}).toFile(path.join(outputDir,`${stem}.jpg`));
const xlsx = await SpreadsheetFile.exportXlsx(wb); await xlsx.save(path.join(outputDir,`${stem}.xlsx`));

const pdf = await PDFDocument.create(); const image = await pdf.embedPng(png); const page = pdf.addPage([841.89,595.28]);
const scale = Math.min((page.getWidth()-40)/image.width,(page.getHeight()-40)/image.height); const w=image.width*scale,h=image.height*scale;
page.drawImage(image,{x:(page.getWidth()-w)/2,y:(page.getHeight()-h)/2,width:w,height:h});
await fs.writeFile(path.join(outputDir,`${stem}.pdf`),await pdf.save());
console.log(JSON.stringify({xlsx:path.join(outputDir,`${stem}.xlsx`),jpg:path.join(outputDir,`${stem}.jpg`),pdf:path.join(outputDir,`${stem}.pdf`)}));
