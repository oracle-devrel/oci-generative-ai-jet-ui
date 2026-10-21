"""Versioned workload used to discover metric candidates in V$SQL."""
# Ontology: a group is every legal entity reachable from its GLEIF root LEI through parent/child edges.
GROUP_LEIS = """SELECT lei FROM GRAPH_TABLE(HF_OWNER.HF_GRAPH
 MATCH (g IS Issuer)-[IS HasEntity]->(root IS LegalEntity)-[IS ParentOf]->{0,4}(e IS LegalEntity)
 WHERE g.alias=:group_name AND root.lei=g.root_lei COLUMNS(e.lei AS lei))"""
BASE = """FROM HF_OWNER.HF_POSITIONS p JOIN HF_OWNER.HF_INSTRUMENTS i ON i.instrument_id=p.instrument_id
JOIN HF_OWNER.HF_ENTITIES e ON e.lei=i.lei
LEFT JOIN HF_OWNER.HF_COLLATERAL c ON c.position_id=p.position_id"""
IN_GROUP = " WHERE i.lei IN (" + GROUP_LEIS + ")"
NET = "p.market_value-SIGN(p.market_value)*LEAST(ABS(p.market_value),NVL(c.eligible_value,0))"
METRICS = {
    "net_exposure": (
        "Signed USD market value minus signed eligible collateral capped at absolute market value; sum over every legal entity reachable from the group root LEI via parent/child links; desk scope enforced by Oracle.",
        f"SELECT /* HF:metric:net_exposure */ NVL(SUM({NET}),0) AS value " + BASE + IN_GROUP,
    ),
    "gross_exposure": (
        "Sum of absolute USD market values, before eligible collateral.",
        "SELECT /* HF:metric:gross_exposure */ NVL(SUM(ABS(p.market_value)),0) AS value "
        + BASE
        + IN_GROUP,
    ),
    "concentration": (
        "Group gross market value / entitled desk NAV × 100. USD base currency. Alert when above 25%.",
        "WITH exposure AS (SELECT NVL(SUM(ABS(p.market_value)),0) AS gross "
        + BASE
        + IN_GROUP
        + ") SELECT /* HF:metric:concentration */ gross/(SELECT SUM(nav) FROM HF_OWNER.HF_DESKS)*100 AS value FROM exposure",
    ),
    "rate_shock": (
        "First order USD P&L for a +200bp parallel rate shift: -market_value × modified duration × 0.02. No convexity.",
        "SELECT /* HF:metric:rate_shock */ NVL(SUM(-p.market_value*i.duration*0.02),0) AS value "
        + BASE
        + IN_GROUP,
    ),
    "liquidity_days": (
        "Maximum position days to exit: ABS(quantity) / (20% of instrument average daily volume); unlimited daily slices, no market impact.",
        "SELECT /* HF:metric:liquidity_days */ NVL(MAX(ABS(p.quantity)/(0.2*i.adv_units)),0) AS value "
        + BASE
        + IN_GROUP,
    ),
    "historical_var": (
        "1-day 99% historical VaR, USD: max(0, minus 1st percentile of 252 daily portfolio P&L observations), current holdings revalued using synthetic daily returns; no normal-distribution approximation.",
        """WITH returns AS (SELECT instrument_id,price_date,price/LAG(price) OVER(PARTITION BY instrument_id ORDER BY price_date)-1 AS r FROM HF_OWNER.HF_PRICES), daily AS (
 SELECT /* HF:metric:historical_var */ r.price_date,SUM(p.market_value*r.r) AS pnl FROM returns r JOIN HF_OWNER.HF_POSITIONS p ON p.instrument_id=r.instrument_id
 JOIN HF_OWNER.HF_INSTRUMENTS i ON i.instrument_id=p.instrument_id
 WHERE r.r IS NOT NULL AND i.lei IN ("""
        + GROUP_LEIS
        + """) GROUP BY r.price_date)
 SELECT GREATEST(0,-PERCENTILE_CONT(0.01) WITHIN GROUP(ORDER BY pnl)) AS value FROM daily""",
    ),
    # Drawdown needs separate analytic passes (nested analytic functions are forbidden).
    "drawdown": (
        "Maximum peak-to-trough percentage loss in compounded equal-weight synthetic instrument-price index over one year; group subset, not realized fund NAV.",
        """WITH normalized AS (
 SELECT pr.price_date,pr.price/FIRST_VALUE(pr.price) OVER(PARTITION BY pr.instrument_id ORDER BY pr.price_date) AS x
 FROM HF_OWNER.HF_PRICES pr JOIN HF_OWNER.HF_INSTRUMENTS i ON i.instrument_id=pr.instrument_id
 WHERE i.lei IN ("""
        + GROUP_LEIS
        + """) AND EXISTS(SELECT 1 FROM HF_OWNER.HF_POSITIONS p WHERE p.instrument_id=i.instrument_id)),
 idx AS(SELECT price_date,AVG(x) AS x FROM normalized GROUP BY price_date), peaks AS(SELECT x,MAX(x) OVER(ORDER BY price_date) peak FROM idx)
 SELECT /* HF:metric:drawdown */ NVL(MAX((peak-x)/peak)*100,0) value FROM peaks""",
    ),
}

# Business vocabulary per approved metric: routes nothing by itself, but validates semantic-cache hits
# so that "gross" never reuses a cached "net" plan just because the sentences are similar.
VOCABULARY = {
    "net_exposure": ["net exposure", "net"],
    "gross_exposure": ["gross exposure", "gross"],
    "concentration": ["concentrat", "% of nav", "percent of nav"],
    "rate_shock": ["rate shock", "rate rise", "200bp", "bp", "duration"],
    "liquidity_days": ["liquidity", "days to exit", "exit", "illiquid"],
    "historical_var": ["var", "value at risk"],
    "drawdown": ["drawdown", "peak-to-trough", "peak to trough"],
}
ACTION_VOCABULARY = {
    "research": ["research", "note", "summar"],
    "rate_positions": ["rate", "200bp", "bp"],
    "liquidity_positions": ["exit", "liquidity", "illiquid"],
    "risk": ["flag", "risk"],
}
