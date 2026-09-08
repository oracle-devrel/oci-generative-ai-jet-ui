import { StyleSheet } from "@react-pdf/renderer";

export const styles = StyleSheet.create({
  page: {
    padding: 48,
    fontSize: 11,
    fontFamily: "Helvetica",
    color: "#111827",
  },
  h1: {
    fontSize: 22,
    fontFamily: "Helvetica-Bold",
    marginBottom: 4,
  },
  h2: {
    fontSize: 14,
    fontFamily: "Helvetica-Bold",
    marginTop: 16,
    marginBottom: 8,
    color: "#1f2937",
  },
  subtle: { color: "#6b7280" },
  row: { flexDirection: "row", marginBottom: 4 },
  label: { width: 110, color: "#6b7280" },
  value: { flex: 1 },
  bold: { fontFamily: "Helvetica-Bold" },
  table: {
    marginTop: 8,
    borderTop: 1,
    borderColor: "#e5e7eb",
  },
  tr: {
    flexDirection: "row",
    borderBottom: 1,
    borderColor: "#e5e7eb",
    paddingVertical: 6,
  },
  th: {
    flexDirection: "row",
    backgroundColor: "#f3f4f6",
    paddingVertical: 6,
    paddingHorizontal: 4,
    fontFamily: "Helvetica-Bold",
  },
  td: { paddingHorizontal: 4 },
  block: { marginTop: 8 },
});
