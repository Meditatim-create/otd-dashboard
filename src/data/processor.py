"""Performance-berekeningen en aggregaties — 6 Logistics Performances."""

import pandas as pd
import numpy as np

from src.utils.constants import (
    PERFORMANCE_STAPPEN, PERFORMANCE_IDS, PERFORMANCE_NAMEN,
    BESCHIKBARE_STAPPEN, BESCHIKBARE_IDS,
)


def join_likp(df_datagrid: pd.DataFrame, df_likp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join Datagrid met LIKP op DeliveryNumber = Levering.
    Voegt Leveringstermijn en Pickdatum toe aan datagrid.

    Retourneert (joined_df, mismatches_df) — mismatches zijn DeliveryNumbers zonder LIKP-match.
    """
    # Selecteer alleen relevante LIKP kolommen
    likp_cols = ["Levering"]
    for col in ["Leveringstermijn", "Pickdatum", "Gecreëerd op"]:
        if col in df_likp.columns:
            likp_cols.append(col)

    likp_subset = df_likp[likp_cols].copy()

    # Join: datagrid.DeliveryNumber = likp.Levering
    # DeliveryNumber kan numeriek of string zijn, Levering ook — forceer naar string
    df = df_datagrid.copy()
    df["_join_key"] = df["DeliveryNumber"].astype(str).str.strip()
    likp_subset["_join_key"] = likp_subset["Levering"].astype(str).str.strip()

    # Drop Levering kolom om dubbele namen te voorkomen
    likp_subset = likp_subset.drop(columns=["Levering"])

    df = df.merge(likp_subset, on="_join_key", how="left")

    # Mismatch detectie: rijen waar Leveringstermijn NaN is na join
    lev_col = "Leveringstermijn" if "Leveringstermijn" in df.columns else None
    if lev_col:
        mismatch_mask = df[lev_col].isna()
    else:
        mismatch_mask = pd.Series(True, index=df.index)

    mismatches = df[mismatch_mask][["DeliveryNumber"]].copy() if mismatch_mask.any() else pd.DataFrame(columns=["DeliveryNumber"])

    df = df.drop(columns=["_join_key"])

    return df, mismatches


def bereken_performances(df: pd.DataFrame) -> pd.DataFrame:
    """Berekent de 6 performance booleans op basis van de beschikbare data.

    1. Planned Performance: Leveringstermijn (LIKP) > SAP Delivery Date → False (Late)
    2. Capacity Performance: PERFORMANCE_CAPACITY != "not moved" → True
    3. Warehouse Performance: PERFORMANCE_LOGISTIC == "On schedule" → True
    4. Carrier Pick-up: geen data → None
    5. Carrier Departure: geen data → None
    6. Carrier Transit: PODDeliveryDateShipment > Leveringstermijn → False (Late)
    """
    df = df.copy()

    # 1. Planned Performance: Leveringstermijn > SAP Delivery Date → Late
    if "Leveringstermijn" in df.columns and "SAP Delivery Date" in df.columns:
        lev = pd.to_datetime(df["Leveringstermijn"], dayfirst=True, errors="coerce")
        sap = pd.to_datetime(df["SAP Delivery Date"], dayfirst=True, errors="coerce")
        # Waar beide datums geldig zijn: on time als Leveringstermijn <= SAP Delivery Date
        df["planned_performance_ok"] = np.where(
            lev.notna() & sap.notna(),
            lev <= sap,
            np.nan,
        )
    else:
        df["planned_performance_ok"] = np.nan

    # 2. Capacity Performance: "not moved" = False, anders True
    if "PERFORMANCE_CAPACITY" in df.columns:
        cap = df["PERFORMANCE_CAPACITY"].astype(str).str.strip().str.lower()
        df["capacity_performance_ok"] = np.where(
            df["PERFORMANCE_CAPACITY"].notna(),
            cap != "not moved",
            np.nan,
        )
    else:
        df["capacity_performance_ok"] = np.nan

    # 3. Warehouse Performance: "On schedule" = True
    if "PERFORMANCE_LOGISTIC" in df.columns:
        wh = df["PERFORMANCE_LOGISTIC"].astype(str).str.strip().str.lower()
        df["warehouse_performance_ok"] = np.where(
            df["PERFORMANCE_LOGISTIC"].notna(),
            wh == "on schedule",
            np.nan,
        )
    else:
        df["warehouse_performance_ok"] = np.nan

    # 4. Carrier Pick-up: geen data
    df["carrier_pickup_ok"] = np.nan

    # 5. Carrier Departure: geen data
    df["carrier_departure_ok"] = np.nan

    # 6. Carrier Transit: PODDeliveryDateShipment > Leveringstermijn → Late
    if "PODDeliveryDateShipment" in df.columns and "Leveringstermijn" in df.columns:
        pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
        lev = pd.to_datetime(df["Leveringstermijn"], dayfirst=True, errors="coerce")
        df["carrier_transit_ok"] = np.where(
            pod.notna() & lev.notna(),
            pod <= lev,
            np.nan,
        )
    else:
        df["carrier_transit_ok"] = np.nan

    # Converteer naar nullable boolean
    for col in PERFORMANCE_IDS:
        if col in df.columns:
            df[col] = df[col].astype("object")  # Bewaar NaN + True/False

    return df


def bereken_otd(df: pd.DataFrame) -> float:
    """Berekent overall On-Time Delivery %.
    OTD = PODDeliveryDateShipment <= RequestedDeliveryDateFinal
    """
    if "PODDeliveryDateShipment" not in df.columns or "RequestedDeliveryDateFinal" not in df.columns:
        return 0.0

    pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
    req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")

    # Alleen rijen meenemen waar beide datums geldig zijn
    valid = pod.notna() & req.notna()
    if valid.sum() == 0:
        return 0.0

    op_tijd = (pod[valid] <= req[valid]).mean() * 100
    return op_tijd


def bereken_kpi_scores(df: pd.DataFrame) -> dict[str, float | None]:
    """Berekent percentage OK per performance-stap.
    Retourneert None voor niet-beschikbare stappen.
    """
    scores = {}
    for stap in PERFORMANCE_STAPPEN:
        kpi_id = stap["id"]
        if not stap["beschikbaar"]:
            scores[kpi_id] = None
            continue
        if kpi_id in df.columns:
            # Filter NaN eruit voor de berekening
            valid = df[kpi_id].dropna()
            if len(valid) > 0:
                scores[kpi_id] = valid.astype(float).mean() * 100
            else:
                scores[kpi_id] = None
        else:
            scores[kpi_id] = None
    return scores


def bereken_root_causes(df: pd.DataFrame) -> pd.DataFrame:
    """Bepaalt voor elke te late order de eerste falende beschikbare stap (root cause).
    Te laat = PODDeliveryDateShipment > RequestedDeliveryDateFinal.
    """
    if "PODDeliveryDateShipment" not in df.columns or "RequestedDeliveryDateFinal" not in df.columns:
        return pd.DataFrame(columns=["DeliveryNumber", "root_cause", "root_cause_naam"])

    pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
    req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")

    valid = pod.notna() & req.notna()
    te_laat = df[valid & (pod > req)].copy()

    if te_laat.empty:
        return pd.DataFrame(columns=["DeliveryNumber", "root_cause", "root_cause_naam"])

    def eerste_faal(row):
        for stap in BESCHIKBARE_STAPPEN:
            kpi_id = stap["id"]
            if kpi_id in row.index:
                val = row[kpi_id]
                # NaN = geen data, skip
                if pd.isna(val):
                    continue
                if not bool(val):
                    return kpi_id
        return "onbekend"

    te_laat["root_cause"] = te_laat.apply(eerste_faal, axis=1)
    te_laat["root_cause_naam"] = te_laat["root_cause"].map(
        lambda x: PERFORMANCE_NAMEN.get(x, "Onbekend")
    )

    id_col = "DeliveryNumber" if "DeliveryNumber" in te_laat.columns else te_laat.columns[0]
    return te_laat[[id_col, "root_cause", "root_cause_naam"]].rename(
        columns={id_col: "DeliveryNumber"}
    )


def root_cause_samenvatting(df: pd.DataFrame) -> pd.DataFrame:
    """Pareto-tabel: root causes gesorteerd op frequentie."""
    rc = bereken_root_causes(df)
    if rc.empty:
        return pd.DataFrame(columns=["root_cause_naam", "aantal", "percentage"])

    telling = rc.groupby("root_cause_naam").size().reset_index(name="aantal")
    telling = telling.sort_values("aantal", ascending=False)
    telling["percentage"] = telling["aantal"] / telling["aantal"].sum() * 100
    telling["cumulatief"] = telling["percentage"].cumsum()
    return telling


def waterval_data(df: pd.DataFrame) -> pd.DataFrame:
    """Berekent data voor de waterval-visualisatie.
    Voor elke beschikbare stap: hoeveel orders falen HIER (eerste faal).
    """
    rc = bereken_root_causes(df)
    totaal_orders = len(df)
    te_laat = len(rc)
    op_tijd = totaal_orders - te_laat

    nummers = "①②③④⑤⑥"
    rijen = [{"stap": "Totaal Orders", "waarde": totaal_orders, "type": "totaal"}]

    for stap in BESCHIKBARE_STAPPEN:
        naam = stap["naam"]
        kpi_id = stap["id"]
        nummer = nummers[stap["nummer"] - 1]
        aantal_faal = len(rc[rc["root_cause"] == kpi_id])
        rijen.append({
            "stap": f"{nummer} {naam}",
            "waarde": -aantal_faal,
            "type": "faal",
        })

    rijen.append({"stap": "Op Tijd Geleverd", "waarde": op_tijd, "type": "ok"})
    return pd.DataFrame(rijen)


def groepeer_per_periode(df: pd.DataFrame, periode_kolom: str = "week") -> pd.DataFrame:
    """Groepeert performance-scores per periode (week of maand)."""
    if periode_kolom not in df.columns:
        return pd.DataFrame()

    # Alleen beschikbare performances groeperen
    cols = [c for c in BESCHIKBARE_IDS if c in df.columns]
    if not cols:
        return pd.DataFrame()

    # Converteer naar float voor aggregatie (NaN wordt genegeerd door mean)
    df_num = df[[periode_kolom] + cols].copy()
    for col in cols:
        df_num[col] = pd.to_numeric(df_num[col], errors="coerce")

    resultaat = df_num.groupby(periode_kolom)[cols].mean() * 100
    resultaat = resultaat.reset_index()
    return resultaat
