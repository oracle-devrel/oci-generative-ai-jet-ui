import type { DeliveryNoteFields } from "@idp/schemas";
import { Card } from "../../components/ui";

export function DeliveryNoteView({ fields }: { fields: DeliveryNoteFields }) {
  return (
    <>
      <Card>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Delivery note
        </h3>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Field label="Delivery note no." value={fields.deliveryNoteNumber} />
          <Field label="PO reference" value={fields.poReference ?? "—"} />
          <Field label="Supplier" value={fields.supplier} />
          <Field label="Recipient" value={fields.recipient} />
          <Field label="Delivery date" value={fields.deliveryDate} />
          <Field label="Carrier" value={fields.carrier ?? "—"} />
          <Field label="Ship to" value={fields.shipTo} />
        </dl>
      </Card>
      <Card className="p-0">
        <h3 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Items delivered
        </h3>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2 text-right">Qty</th>
              <th className="px-4 py-2 text-right">Unit</th>
            </tr>
          </thead>
          <tbody>
            {fields.lineItems.map((item, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-4 py-2">{item.description}</td>
                <td className="px-4 py-2 text-right">{item.quantity}</td>
                <td className="px-4 py-2 text-right">{item.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
