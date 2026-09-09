import React from "react";
import { Document, Page, View, Text } from "@react-pdf/renderer";
import { styles } from "./styles.js";
import type { PurchaseOrderFields } from "@idp/schemas";

export function PurchaseOrderPDF({ data }: { data: PurchaseOrderFields }) {
  const money = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: data.currency }).format(n);

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.h1}>PURCHASE ORDER</Text>
        <Text style={styles.subtle}>{data.poNumber}</Text>

        <View style={styles.block}>
          <View style={styles.row}>
            <Text style={styles.label}>Buyer</Text>
            <Text style={styles.value}>{data.buyer}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Supplier</Text>
            <Text style={styles.value}>{data.supplier}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Order date</Text>
            <Text style={styles.value}>{data.orderDate}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Expected delivery</Text>
            <Text style={styles.value}>{data.expectedDeliveryDate ?? "—"}</Text>
          </View>
          {data.shipTo != null && (
            <View style={styles.row}>
              <Text style={styles.label}>Ship to</Text>
              <Text style={styles.value}>{data.shipTo}</Text>
            </View>
          )}
        </View>

        <Text style={styles.h2}>Line items</Text>
        <View>
          <View style={styles.th}>
            <Text style={{ flex: 4 }}>Description</Text>
            <Text style={{ width: 50, textAlign: "right" }}>Qty</Text>
            <Text style={{ width: 70, textAlign: "right" }}>Unit</Text>
            <Text style={{ width: 80, textAlign: "right" }}>Total</Text>
          </View>
          {data.lineItems.map((item, i) => (
            <View key={i} style={styles.tr}>
              <Text style={{ flex: 4, ...styles.td }}>{item.description}</Text>
              <Text style={{ width: 50, textAlign: "right", ...styles.td }}>{item.quantity}</Text>
              <Text style={{ width: 70, textAlign: "right", ...styles.td }}>
                {money(item.unitPrice)}
              </Text>
              <Text style={{ width: 80, textAlign: "right", ...styles.td }}>
                {money(item.total)}
              </Text>
            </View>
          ))}
        </View>

        <View style={{ marginTop: 16, alignSelf: "flex-end", width: 220 }}>
          <View style={styles.row}>
            <Text style={styles.label}>Subtotal</Text>
            <Text style={styles.value}>{money(data.subtotal)}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Tax</Text>
            <Text style={styles.value}>{money(data.tax)}</Text>
          </View>
          <View style={styles.row}>
            <Text style={[styles.label, styles.bold]}>Total</Text>
            <Text style={[styles.value, styles.bold]}>{money(data.total)}</Text>
          </View>
        </View>
      </Page>
    </Document>
  );
}
