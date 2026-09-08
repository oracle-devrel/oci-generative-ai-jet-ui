"""Geospatial proximity search using Oracle Spatial SDO_GEOMETRY."""

from database.query_helper import execute_query


def find_nearby_clients(conn, account_id, radius_km=500, top_k=10, query_logger=None):
    """Find client accounts within a given radius of a target account.

    Uses SDO_WITHIN_DISTANCE with an R-tree spatial index on SDO_GEOMETRY points.
    """
    sql = f"""
        SELECT b.account_id, b.client_name, b.risk_profile, b.aum,
               ROUND(SDO_GEOM.SDO_DISTANCE(a.location, b.location, 0.005, 'unit=KM'), 1)
                   AS distance_km
        FROM client_accounts a, client_accounts b
        WHERE a.account_id = :account_id
          AND b.account_id <> a.account_id
          AND b.location IS NOT NULL
          AND a.location IS NOT NULL
          AND SDO_WITHIN_DISTANCE(b.location, a.location,
                                  'distance={radius_km} unit=KM') = 'TRUE'
        ORDER BY distance_km
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Spatial search: clients within {radius_km}km of {account_id}",
    )


def find_nearest_rm(conn, account_id, top_k=3, query_logger=None):
    """Find the nearest relationship managers to a client account.

    Uses SDO_NN (nearest neighbor) with spatial index for efficient proximity ranking.
    """
    sql = f"""
        SELECT rm.rm_id, rm.rm_name, rm.region, rm.team,
               ROUND(SDO_GEOM.SDO_DISTANCE(ca.location, rm.office_location, 0.005, 'unit=KM'), 1)
                   AS distance_km
        FROM client_accounts ca, relationship_managers rm
        WHERE ca.account_id = :account_id
          AND ca.location IS NOT NULL
          AND rm.office_location IS NOT NULL
          AND SDO_NN(rm.office_location, ca.location, 'unit=KM') = 'TRUE'
        ORDER BY distance_km
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Spatial search: nearest RMs to {account_id}",
    )
