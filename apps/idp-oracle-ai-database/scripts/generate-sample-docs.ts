import { mkdir, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { faker } from "@faker-js/faker";
import { renderToBuffer } from "@react-pdf/renderer";
import { createElement } from "react";
import { InvoicePDF } from "./templates/InvoicePDF.js";
import { PurchaseOrderPDF } from "./templates/PurchaseOrderPDF.js";
import { DeliveryNotePDF } from "./templates/DeliveryNotePDF.js";
import { makeInvoice, makePurchaseOrder, makeDeliveryNote } from "./templates/factories.js";

type DocType = "invoice" | "purchase_order" | "delivery_note";

interface Args {
  count: number;
  type: DocType | "all";
  seed: number;
  out: string;
}

const ALL_TYPES: DocType[] = ["invoice", "purchase_order", "delivery_note"];

const TYPE_META: Record<DocType, { subdir: string; prefix: string }> = {
  invoice: { subdir: "invoices", prefix: "invoice" },
  purchase_order: { subdir: "purchase-orders", prefix: "purchase-order" },
  delivery_note: { subdir: "delivery-notes", prefix: "delivery-note" },
};

function parseArgs(argv: string[]): Args {
  const args: Args = {
    count: 10,
    type: "all",
    seed: 42,
    out: join(dirname(fileURLToPath(import.meta.url)), "..", "samples"),
  };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    const val = argv[i + 1];
    if (!key || val === undefined) break;
    if (key === "--count") args.count = Number(val);
    else if (key === "--type") args.type = val as Args["type"];
    else if (key === "--seed") args.seed = Number(val);
    else if (key === "--out") args.out = val;
  }
  return args;
}

async function writePdf(node: React.ReactElement, outPath: string): Promise<void> {
  await mkdir(dirname(outPath), { recursive: true });
  const buffer = await renderToBuffer(node);
  await writeFile(outPath, buffer);
}

async function generateOne(type: DocType, idx: number, outDir: string): Promise<string> {
  const padded = String(idx + 1).padStart(2, "0");
  const { subdir, prefix } = TYPE_META[type];
  const file = join(outDir, subdir, `${prefix}-${padded}.pdf`);

  if (type === "invoice") {
    await writePdf(createElement(InvoicePDF, { data: makeInvoice() }), file);
  } else if (type === "purchase_order") {
    await writePdf(createElement(PurchaseOrderPDF, { data: makePurchaseOrder() }), file);
  } else {
    await writePdf(createElement(DeliveryNotePDF, { data: makeDeliveryNote() }), file);
  }
  return file;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  faker.seed(args.seed);
  const types: DocType[] = args.type === "all" ? ALL_TYPES : [args.type];

  console.log(`generating ${args.count} of each [${types.join(", ")}] with seed ${args.seed}`);
  for (const t of types) {
    for (let i = 0; i < args.count; i++) {
      const path = await generateOne(t, i, args.out);
      console.log(`  ${path}`);
    }
  }
  console.log("done");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
