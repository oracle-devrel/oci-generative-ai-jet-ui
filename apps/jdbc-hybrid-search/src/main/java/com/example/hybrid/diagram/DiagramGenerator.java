package com.example.hybrid.diagram;

import javax.sql.DataSource;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Writes a simple radial SVG where radius encodes cosine distance from the center tutorial.
 * Angle is only used to separate points visually.
 */
public final class DiagramGenerator {
    private static final String CENTER_TITLE = "Oracle Vector Search for Beginners";
    private static final String BUDGET_TITLE = "Budget-Friendly Hybrid Search Recipes";
    private static final String TUNING_TITLE = "Production Hybrid Search Tuning";
    private static final String TEXT_TITLE = "Beginner Text Search with Oracle Text";

    private static final int WIDTH = 1360;
    private static final int HEIGHT = 760;
    private static final int TOP_PADDING = 140;
    private static final int BOTTOM_PADDING = 80;
    private static final double PANEL_X = 40.0d;
    private static final double PANEL_Y = 120.0d;
    private static final double PANEL_MIN_WIDTH = 520.0d;
    private static final double PANEL_GRAPH_GAP = 40.0d;
    private static final double GRAPH_RIGHT_PADDING = 80.0d;
    private static final double PANEL_CHAR_WIDTH = 6.4d;
    private static final double TABLE_ROW_HEIGHT = 26.0d;
    private static final double LEGEND_ROW_GAP = 28.0d;
    private static final double RADIAL_MARGIN = 42.0d;
    private static final int GUIDE_RING_COUNT = 4;
    private static final double LINE_LABEL_WIDTH = 62.0d;
    private static final double LINE_LABEL_HEIGHT = 20.0d;
    private static final double LINE_LABEL_TEXT_INSET_X = 8.0d;
    private static final double LINE_LABEL_TEXT_BASELINE = 14.0d;
    private static final Path OUTPUT_PATH = Path.of("jdbc-hybrid-search", "hybrid-search-diagram.svg");

    private final DiagramRepository plotData;

    public DiagramGenerator(DataSource dataSource) {
        this.plotData = new DiagramRepository(dataSource);
    }

    public void writeSvg() throws IOException {
        Files.createDirectories(OUTPUT_PATH.toAbsolutePath().getParent());
        Files.writeString(OUTPUT_PATH, buildSvg());
        System.out.println("Hybrid search diagram written to: " + OUTPUT_PATH.toAbsolutePath());
    }

    public String buildSvg() {
        List<DiagramDocument> documents = plotData.listDiagramDocuments();
        List<Measurement> measurements = List.of(
                highlightedDistance(BUDGET_TITLE, 1036.0d, 372.0d),
                highlightedDistance(TUNING_TITLE, 818.0d, 456.0d),
                highlightedDistance(TEXT_TITLE, 874.0d, 349.0d)
        );

        DiagramLayout layout = layout(documents);
        List<DocumentDistance> documentDistances = documentDistances(documents);
        List<PointReference> references = pointReferences(documentDistances, layout);
        Map<String, PointReference> referencesByTitle = indexReferencesByTitle(references);

        StringBuilder svg = new StringBuilder();
        svg.append("""
                <svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">
                  <style>
                    text { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; fill: #111827; }
                    .title { font-size: 28px; font-weight: 700; }
                    .subtitle { font-size: 14px; fill: #4b5563; }
                    .tutorial { fill: #0f766e; stroke: white; stroke-width: 2; }
                    .reference { fill: #1d4ed8; stroke: white; stroke-width: 2; }
                    .beginner-ring { fill: none; stroke: #f59e0b; stroke-width: 2; }
                    .line { stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6 4; }
                    .point-number { font-size: 10px; font-weight: 700; fill: white; text-anchor: middle; dominant-baseline: middle; }
                    .line-label-box { fill: rgba(248,250,252,0.96); stroke: #cbd5e1; stroke-width: 1; rx: 5; ry: 5; }
                    .line-label { font-size: 11px; font-weight: 700; fill: #1f2937; }
                    .panel { fill: #f8fafc; stroke: #bfdbfe; stroke-width: 1; rx: 10; ry: 10; }
                    .plot-frame { fill: rgba(255,255,255,0.45); stroke: #bfdbfe; stroke-width: 1.5; rx: 14; ry: 14; }
                    .guide-ring { fill: none; stroke: #dbeafe; stroke-width: 1; }
                    .guide-label { font-size: 11px; fill: #64748b; }
                    .panel-header { font-size: 13px; font-weight: 700; fill: #1e3a8a; }
                    .panel-row { font-size: 12px; fill: #1f2937; }
                    .panel-value { font-size: 12px; font-weight: 700; fill: #1d4ed8; }
                    .legend { font-size: 13px; fill: #374151; }
                  </style>
                  <rect x="0" y="0" width="%d" height="%d" fill="#f8fafc"/>
                  <text x="60" y="46" class="title">Hybrid Search Distance Map</text>
                  <text x="60" y="70" class="subtitle">Oracle Vector Search for Beginners is fixed at the center and every other point radius is scaled directly from cosine distance</text>
                  <text x="60" y="90" class="subtitle">Angles are only for separation; the distance from the center point is the meaningful quantity in this chart</text>
                  <text x="60" y="110" class="subtitle">Dashed lines show selected relationships from the center and are labeled with exact cosine distance</text>
                """.formatted(WIDTH, HEIGHT, WIDTH, HEIGHT, WIDTH, HEIGHT));

        svg.append(referenceTableSvg(references, layout));
        svg.append(plotFrameSvg(layout));
        svg.append(guideRingsSvg(layout, references));

        for (Measurement measurement : measurements) {
            svg.append(lineSvg(
                    referenceByTitle(referencesByTitle, measurement.fromTitle()).point(),
                    referenceByTitle(referencesByTitle, measurement.toTitle()).point()
            ));
        }
        for (Measurement measurement : measurements) {
            svg.append(lineLabelSvg(new LineLabelPlacement(
                    measurement.labelX(),
                    measurement.labelY(),
                    measurement.distance()
            )));
        }
        for (PointReference reference : references) {
            svg.append(pointSvg(reference));
        }

        svg.append(legendSvg(references.size()));
        svg.append("""
                </svg>
                """);
        return svg.toString();
    }

    private Measurement highlightedDistance(String title, double labelX, double labelY) {
        return new Measurement(
                CENTER_TITLE,
                title,
                plotData.cosineDistanceBetween(CENTER_TITLE, title),
                labelX,
                labelY
        );
    }

    private List<DocumentDistance> documentDistances(List<DiagramDocument> documents) {
        List<DocumentDistance> distances = new ArrayList<>();
        for (DiagramDocument document : documents) {
            double distance = document.title().equals(CENTER_TITLE)
                    ? 0.0d
                    : plotData.cosineDistanceBetween(CENTER_TITLE, document.title());
            distances.add(new DocumentDistance(document, distance));
        }
        return distances;
    }

    private List<PointReference> pointReferences(List<DocumentDistance> documentDistances, DiagramLayout layout) {
        double maxDistance = documentDistances.stream()
                .mapToDouble(DocumentDistance::distanceFromCenter)
                .max()
                .orElse(1.0d);
        double maxRadius = Math.min(layout.graphRight() - layout.graphLeft(), layout.graphBottom() - layout.graphTop()) / 2.0d - RADIAL_MARGIN;
        double centerX = (layout.graphLeft() + layout.graphRight()) / 2.0d;
        double centerY = (layout.graphTop() + layout.graphBottom()) / 2.0d;

        List<DocumentDistance> orderedDistances = orderedDocumentDistances(documentDistances);
        List<DocumentDistance> outer = orderedDistances.stream()
                .filter(distance -> !distance.document().title().equals(CENTER_TITLE))
                .toList();
        Map<String, ScreenPoint> pointsByTitle = new LinkedHashMap<>();
        pointsByTitle.put(CENTER_TITLE, new ScreenPoint(centerX, centerY));

        for (int i = 0; i < outer.size(); i++) {
            DocumentDistance distance = outer.get(i);
            double angle = (-Math.PI / 2.0d) + ((2.0d * Math.PI * i) / outer.size());
            double radius = maxDistance == 0.0d ? 0.0d : (distance.distanceFromCenter() / maxDistance) * maxRadius;
            pointsByTitle.put(
                    distance.document().title(),
                    new ScreenPoint(
                            centerX + (Math.cos(angle) * radius),
                            centerY + (Math.sin(angle) * radius)
                    )
            );
        }

        List<PointReference> references = new ArrayList<>();
        for (int i = 0; i < orderedDistances.size(); i++) {
            DocumentDistance distance = orderedDistances.get(i);
            references.add(new PointReference(i + 1, distance.document(), distance.distanceFromCenter(), pointsByTitle.get(distance.document().title())));
        }
        return references;
    }

    private List<DocumentDistance> orderedDocumentDistances(List<DocumentDistance> documentDistances) {
        return documentDistances.stream()
                .sorted(Comparator
                        .comparing((DocumentDistance distance) -> !distance.document().title().equals(CENTER_TITLE))
                        .thenComparing(distance -> distance.document().title()))
                .toList();
    }

    private String referenceTableSvg(List<PointReference> references, DiagramLayout layout) {
        double height = tableHeight(references.size());
        StringBuilder panel = new StringBuilder("""
                  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" class="panel"/>
                  <text x="58" y="148" class="panel-header">Point Reference</text>
                """.formatted(PANEL_X, PANEL_Y, layout.panelWidth(), height));

        for (int i = 0; i < references.size(); i++) {
            PointReference reference = references.get(i);
            double rowY = PANEL_Y + 40.0d + (i * TABLE_ROW_HEIGHT);
            String title = reference.document().title().equals(CENTER_TITLE)
                    ? reference.document().title() + " (center)"
                    : reference.document().title();
            panel.append("""
                      <text x="58" y="%.2f" class="panel-value">%d</text>
                      <text x="100" y="%.2f" class="panel-row">%s</text>
                    """.formatted(
                    rowY,
                    reference.number(),
                    rowY,
                    title
            ));
        }
        return panel.toString();
    }

    private String plotFrameSvg(DiagramLayout layout) {
        return """
                  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" class="plot-frame"/>
                """.formatted(
                layout.graphLeft() - 18.0d,
                layout.graphTop() - 18.0d,
                (layout.graphRight() - layout.graphLeft()) + 36.0d,
                (layout.graphBottom() - layout.graphTop()) + 36.0d
        );
    }

    private String guideRingsSvg(DiagramLayout layout, List<PointReference> references) {
        double centerX = (layout.graphLeft() + layout.graphRight()) / 2.0d;
        double centerY = (layout.graphTop() + layout.graphBottom()) / 2.0d;
        double maxRadius = Math.min(layout.graphRight() - layout.graphLeft(), layout.graphBottom() - layout.graphTop()) / 2.0d - RADIAL_MARGIN;
        double maxDistance = references.stream().mapToDouble(PointReference::distanceFromCenter).max().orElse(1.0d);

        StringBuilder rings = new StringBuilder();
        for (int i = 1; i <= GUIDE_RING_COUNT; i++) {
            double radius = (maxRadius * i) / GUIDE_RING_COUNT;
            double distanceValue = (maxDistance * i) / GUIDE_RING_COUNT;
            rings.append("""
                      <circle cx="%.2f" cy="%.2f" r="%.2f" class="guide-ring"/>
                      <text x="%.2f" y="%.2f" class="guide-label">%.3f</text>
                    """.formatted(
                    centerX,
                    centerY,
                    radius,
                    centerX + radius + 8.0d,
                    centerY - 4.0d,
                    distanceValue
            ));
        }
        return rings.toString();
    }

    private String pointSvg(PointReference reference) {
        ScreenPoint point = reference.point();
        String cssClass = "tutorial".equals(reference.document().category()) ? "tutorial" : "reference";

        StringBuilder marker = new StringBuilder();
        marker.append("""
                  <circle cx="%.2f" cy="%.2f" r="11" class="%s"/>
                """.formatted(point.x(), point.y(), cssClass));
        if ("beginner".equals(reference.document().audience())) {
            marker.append("""
                      <circle cx="%.2f" cy="%.2f" r="16" class="beginner-ring"/>
                    """.formatted(point.x(), point.y()));
        }
        marker.append("""
                  <text x="%.2f" y="%.2f" class="point-number">%d</text>
                """.formatted(point.x(), point.y(), reference.number()));
        return marker.toString();
    }

    private String lineSvg(ScreenPoint from, ScreenPoint to) {
        return """
                  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="line"/>
                """.formatted(from.x(), from.y(), to.x(), to.y());
    }

    private String lineLabelSvg(LineLabelPlacement label) {
        return """
                  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" class="line-label-box"/>
                  <text x="%.2f" y="%.2f" class="line-label">%.4f</text>
                """.formatted(
                label.x() - (LINE_LABEL_WIDTH / 2.0d),
                label.y() - (LINE_LABEL_HEIGHT / 2.0d),
                LINE_LABEL_WIDTH,
                LINE_LABEL_HEIGHT,
                label.x() - (LINE_LABEL_WIDTH / 2.0d) + LINE_LABEL_TEXT_INSET_X,
                label.y() - (LINE_LABEL_HEIGHT / 2.0d) + LINE_LABEL_TEXT_BASELINE,
                label.distance()
        );
    }

    private String legendSvg(int documentCount) {
        double baseY = PANEL_Y + tableHeight(documentCount) + 36.0d;
        double ringY = baseY + (LEGEND_ROW_GAP * 2.0d);
        double lineY = baseY + (LEGEND_ROW_GAP * 3.0d);
        return """
                  <circle cx="60" cy="%.2f" r="8" class="tutorial"/>
                  <text x="78" y="%.2f" class="legend">Green points: tutorials</text>
                  <circle cx="60" cy="%.2f" r="8" class="reference"/>
                  <text x="78" y="%.2f" class="legend">Blue points: reference material</text>
                  <circle cx="60" cy="%.2f" r="8" class="tutorial"/>
                  <circle cx="60" cy="%.2f" r="13" class="beginner-ring"/>
                  <text x="78" y="%.2f" class="legend">Gold rings: beginner audience</text>
                  <line x1="42" y1="%.2f" x2="78" y2="%.2f" class="line"/>
                  <text x="88" y="%.2f" class="legend">Dashed lines: cosine distances from center</text>
                """.formatted(
                baseY,
                baseY + 5.0d,
                baseY + LEGEND_ROW_GAP,
                baseY + LEGEND_ROW_GAP + 5.0d,
                ringY,
                ringY,
                ringY + 5.0d,
                lineY,
                lineY,
                lineY + 5.0d
        );
    }

    private Map<String, PointReference> indexReferencesByTitle(List<PointReference> references) {
        Map<String, PointReference> referencesByTitle = new LinkedHashMap<>();
        for (PointReference reference : references) {
            referencesByTitle.put(reference.document().title(), reference);
        }
        return referencesByTitle;
    }

    private PointReference referenceByTitle(Map<String, PointReference> referencesByTitle, String title) {
        PointReference reference = referencesByTitle.get(title);
        if (reference == null) {
            throw new IllegalArgumentException("No point reference found for " + title);
        }
        return reference;
    }

    private double tableHeight(int documentCount) {
        return 40.0d + (documentCount * TABLE_ROW_HEIGHT) + 32.0d;
    }

    private DiagramLayout layout(List<DiagramDocument> documents) {
        double panelWidth = PANEL_MIN_WIDTH;
        for (DiagramDocument document : documents) {
            panelWidth = Math.max(panelWidth, 110.0d + (document.title().length() * PANEL_CHAR_WIDTH));
        }
        double graphLeft = PANEL_X + panelWidth + PANEL_GRAPH_GAP;
        double graphRight = WIDTH - GRAPH_RIGHT_PADDING;
        double graphTop = TOP_PADDING;
        double graphBottom = HEIGHT - BOTTOM_PADDING;
        return new DiagramLayout(panelWidth, graphLeft, graphRight, graphTop, graphBottom);
    }

    private record DocumentDistance(DiagramDocument document, double distanceFromCenter) {
    }

    private record Measurement(String fromTitle, String toTitle, double distance, double labelX, double labelY) {
    }

    private record DiagramLayout(double panelWidth, double graphLeft, double graphRight, double graphTop, double graphBottom) {
    }

    private record PointReference(int number, DiagramDocument document, double distanceFromCenter, ScreenPoint point) {
    }

    private record ScreenPoint(double x, double y) {
    }

    private record LineLabelPlacement(double x, double y, double distance) {
    }
}
