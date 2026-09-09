import { faker } from "@faker-js/faker";
import type { InvoiceFields, PurchaseOrderFields, DeliveryNoteFields } from "@idp/schemas";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

interface PricedLine {
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
}

function makeLineItems(min: number, max: number, priceMin: number, priceMax: number): PricedLine[] {
  const count = faker.number.int({ min, max });
  return Array.from({ length: count }, () => {
    const quantity = faker.number.int({ min: 1, max: 20 });
    const unitPrice = Number(faker.commerce.price({ min: priceMin, max: priceMax }));
    return {
      description: faker.commerce.productName(),
      quantity,
      unitPrice,
      total: Number((quantity * unitPrice).toFixed(2)),
    };
  });
}

function totals(lineItems: PricedLine[], taxRate = 0.19) {
  const subtotal = Number(lineItems.reduce((s, l) => s + l.total, 0).toFixed(2));
  const tax = Number((subtotal * taxRate).toFixed(2));
  const total = Number((subtotal + tax).toFixed(2));
  return { subtotal, tax, total };
}

export function makeInvoice(): InvoiceFields {
  const lineItems = makeLineItems(1, 12, 50, 2500);
  const { subtotal, tax, total } = totals(lineItems);
  const invoiceDate = faker.date.recent({ days: 90 });
  const dueDate = new Date(invoiceDate.getTime() + 30 * 24 * 60 * 60 * 1000);

  return {
    envelope: {
      docType: "invoice",
      summary: `Invoice from ${faker.company.name()}`,
      language: "en",
      pageCount: 1,
      confidence: 1,
    },
    vendor: faker.company.name(),
    invoiceNumber: `INV-${faker.number.int({ min: 1000, max: 9999 })}`,
    invoiceDate: isoDate(invoiceDate),
    dueDate: isoDate(dueDate),
    currency: "USD",
    subtotal,
    tax,
    total,
    lineItems,
  };
}

export function makePurchaseOrder(): PurchaseOrderFields {
  const lineItems = makeLineItems(2, 10, 80, 3000);
  const { subtotal, tax, total } = totals(lineItems);
  const orderDate = faker.date.recent({ days: 60 });
  const expectedDeliveryDate = new Date(orderDate.getTime() + 14 * 24 * 60 * 60 * 1000);
  const buyer = faker.company.name();

  return {
    envelope: {
      docType: "purchase_order",
      summary: `Purchase order from ${buyer}`,
      language: "en",
      pageCount: 1,
      confidence: 1,
    },
    poNumber: `PO-${faker.number.int({ min: 10000, max: 99999 })}`,
    buyer,
    supplier: faker.company.name(),
    orderDate: isoDate(orderDate),
    expectedDeliveryDate: isoDate(expectedDeliveryDate),
    shipTo: `${faker.location.streetAddress()}, ${faker.location.city()}, ${faker.location.countryCode()}`,
    currency: "USD",
    subtotal,
    tax,
    total,
    lineItems,
  };
}

const UNITS = ["pcs", "boxes", "pallets", "cartons", "units", "kg", "reels"];
const CARRIERS = ["DHL Freight", "UPS", "FedEx Ground", "DB Schenker", "Kuehne + Nagel"];

export function makeDeliveryNote(): DeliveryNoteFields {
  const itemCount = faker.number.int({ min: 2, max: 9 });
  const lineItems = Array.from({ length: itemCount }, () => ({
    description: faker.commerce.productName(),
    quantity: faker.number.int({ min: 1, max: 40 }),
    unit: faker.helpers.arrayElement(UNITS),
  }));
  const supplier = faker.company.name();
  const recipient = faker.company.name();

  return {
    envelope: {
      docType: "delivery_note",
      summary: `Delivery note from ${supplier} to ${recipient}`,
      language: "en",
      pageCount: 1,
      confidence: 1,
    },
    deliveryNoteNumber: `DN-${faker.number.int({ min: 10000, max: 99999 })}`,
    poReference: `PO-${faker.number.int({ min: 10000, max: 99999 })}`,
    supplier,
    recipient,
    deliveryDate: isoDate(faker.date.recent({ days: 30 })),
    shipTo: `${faker.location.streetAddress()}, ${faker.location.city()}, ${faker.location.countryCode()}`,
    carrier: faker.helpers.arrayElement(CARRIERS),
    lineItems,
  };
}
