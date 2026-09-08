import React from "react";
import { Document, Page, View, Text } from "@react-pdf/renderer";
import { styles } from "./styles.js";
import type { DeliveryNoteFields } from "@idp/schemas";

export function DeliveryNotePDF({ data }: { data: DeliveryNoteFields }) {
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.h1}>DELIVERY NOTE</Text>
        <Text style={styles.subtle}>{data.deliveryNoteNumber}</Text>

        <View style={styles.block}>
          <View style={styles.row}>
            <Text style={styles.label}>Supplier</Text>
            <Text style={styles.value}>{data.supplier}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Recipient</Text>
            <Text style={styles.value}>{data.recipient}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Delivery date</Text>
            <Text style={styles.value}>{data.deliveryDate}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>PO reference</Text>
            <Text style={styles.value}>{data.poReference ?? "—"}</Text>
          </View>
          {data.carrier != null && (
            <View style={styles.row}>
              <Text style={styles.label}>Carrier</Text>
              <Text style={styles.value}>{data.carrier}</Text>
            </View>
          )}
          <View style={styles.row}>
            <Text style={styles.label}>Ship to</Text>
            <Text style={styles.value}>{data.shipTo}</Text>
          </View>
        </View>

        <Text style={styles.h2}>Items delivered</Text>
        <View>
          <View style={styles.th}>
            <Text style={{ flex: 5 }}>Description</Text>
            <Text style={{ width: 60, textAlign: "right" }}>Qty</Text>
            <Text style={{ width: 80, textAlign: "right" }}>Unit</Text>
          </View>
          {data.lineItems.map((item, i) => (
            <View key={i} style={styles.tr}>
              <Text style={{ flex: 5, ...styles.td }}>{item.description}</Text>
              <Text style={{ width: 60, textAlign: "right", ...styles.td }}>{item.quantity}</Text>
              <Text style={{ width: 80, textAlign: "right", ...styles.td }}>{item.unit}</Text>
            </View>
          ))}
        </View>

        <View style={{ marginTop: 24 }}>
          <Text style={styles.label}>Received by ______________________</Text>
        </View>
      </Page>
    </Document>
  );
}
