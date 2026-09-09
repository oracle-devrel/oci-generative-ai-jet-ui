import type { InvoiceFields } from "@idp/schemas";
import { Card } from "../../components/ui";

export function InvoiceView({ fields }: { fields: InvoiceFields }) {
  const fmt = (n: number) =>
    new Intl.NumberFormat(undefined, { style: "currency", currency: fields.currency }).format(n);
  return (
    <>
      <Card>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Invoice
        </h3>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Field label="Vendor" value={fields.vendor} />
          <Field label="Number" value={fields.invoiceNumber} />
          <Field label="Invoice date" value={fields.invoiceDate} />
          <Field label="Due date" value={fields.dueDate ?? "—"} />
          <Field label="Subtotal" value={fmt(fields.subtotal)} />
          <Field label="Tax" value={fmt(fields.tax)} />
          <Field label="Total" value={fmt(fields.total)} bold />
        </dl>
      </Card>
      <Card className="p-0">
        <h3 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Line items
        </h3>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2 text-right">Qty</th>
              <th className="px-4 py-2 text-right">Unit</th>
              <th className="px-4 py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {fields.lineItems.map((item, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-4 py-2">{item.description}</td>
                <td className="px-4 py-2 text-right">{item.quantity}</td>
                <td className="px-4 py-2 text-right">{fmt(item.unitPrice)}</td>
                <td className="px-4 py-2 text-right">{fmt(item.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

function Field({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={bold ? "font-semibold" : ""}>{value}</dd>
    </div>
  );
}
