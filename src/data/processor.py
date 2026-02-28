"""Performance-berekeningen en aggregaties — 6 Logistics Performances.

Berekeningen zijn config-driven via rekenmodel.yaml:
- method: "column" → lees pre-berekende PowerBI-kolom
- method: "recalculate" → herbereken uit datumkolommen
"""

import pandas as pd
import numpy as np

from src.config import get_otd_config, get_performance_config, get_alle_performances
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


# --- Helpers voor config-driven berekeningen ---

def _bereken_from_column(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """Lees een PowerBI-kolom en map waarden naar bool (True/False/NaN).

    cfg verwacht: source_column, ok_values, optioneel no_pod_values.
    """
    source_column = cfg.get("source_column", "")
    ok_values = cfg.get("ok_values", [])
    no_pod_values = cfg.get("no_pod_values", [])

    if source_column not in df.columns:
        return pd.Series(np.nan, index=df.index)

    col = df[source_column].astype(str).str.strip().str.lower()
    ok_lower = [v.lower() for v in ok_values]

    result = pd.Series(np.nan, index=df.index, dtype="object")

    # Alleen waar de bron niet-leeg is
    niet_leeg = df[source_column].notna()
    result[niet_leeg] = col[niet_leeg].isin(ok_lower).values

    # No-POD waarden → NaN (uitsluiten van noemer)
    if no_pod_values:
        no_pod_lower = [v.lower() for v in no_pod_values]
        is_no_pod = col.isin(no_pod_lower)
        result[is_no_pod] = np.nan

    return result


def _bereken_from_dates(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """Herbereken performance uit twee datumkolommen: dates[0] <= dates[1] → OK.

    cfg verwacht: dates (lijst van 2 kolomnamen).
    """
    dates = cfg.get("dates", [])
    if len(dates) < 2:
        return pd.Series(np.nan, index=df.index)

    col_a, col_b = dates[0], dates[1]
    if col_a not in df.columns or col_b not in df.columns:
        return pd.Series(np.nan, index=df.index)

    date_a = pd.to_datetime(df[col_a], dayfirst=True, errors="coerce")
    date_b = pd.to_datetime(df[col_b], dayfirst=True, errors="coerce")

    return pd.Series(
        np.where(
            date_a.notna() & date_b.notna(),
            date_a <= date_b,
            np.nan,
        ),
        index=df.index,
    )


def _bereken_performance(df: pd.DataFrame, kpi_id: str) -> pd.Series:
    """Bereken één performance-stap op basis van config (column of recalculate)."""
    cfg = get_performance_config(kpi_id)

    if not cfg.get("beschikbaar", False):
        return pd.Series(np.nan, index=df.index)

    method = cfg.get("method", "")
    if method == "column":
        return _bereken_from_column(df, cfg)
    elif method == "recalculate":
        return _bereken_from_dates(df, cfg)
    else:
        return pd.Series(np.nan, index=df.index)


# --- Hoofd-functies ---

def bereken_performances(df: pd.DataFrame) -> pd.DataFrame:
    """Berekent de 6 performance booleans op basis van rekenmodel.yaml.

    Per KPI wordt de methode (column of recalculate) bepaald door de config.
    Voegt ook otd_ok kolom toe.
    """
    df = df.copy()

    # Bereken elke performance-stap via config
    performances = get_alle_performances()
    for kpi_id in performances:
        df[kpi_id] = _bereken_performance(df, kpi_id)

    # OTD als kolom toevoegen (voor root cause analyse)
    otd_cfg = get_otd_config()
    if otd_cfg.get("method") == "column":
        df["otd_ok"] = _bereken_from_column(df, otd_cfg)
    else:
        # Recalculate: POD <= RequestedDeliveryDateFinal
        if "PODDeliveryDateShipment" in df.columns and "RequestedDeliveryDateFinal" in df.columns:
            pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
            req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
            df["otd_ok"] = np.where(
                pod.notna() & req.notna(),
                pod <= req,
                np.nan,
            )
        else:
            df["otd_ok"] = np.nan

    # Converteer naar nullable boolean (object type bewaart NaN + True/False)
    for col in list(performances.keys()) + ["otd_ok"]:
        if col in df.columns:
            df[col] = df[col].astype("object")

    return df


def bereken_otd(df: pd.DataFrame) -> float:
    """Berekent overall On-Time Delivery %.

    Gebruikt otd_ok kolom als beschikbaar (config-driven), anders fallback naar datums.
    """
    # Gebruik pre-berekende otd_ok kolom als die er is
    if "otd_ok" in df.columns:
        valid = df["otd_ok"].dropna()
        if len(valid) == 0:
            return 0.0
        return valid.astype(float).mean() * 100

    # Fallback: herbereken uit datums
    if "PODDeliveryDateShipment" not in df.columns or "RequestedDeliveryDateFinal" not in df.columns:
        return 0.0

    pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
    req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")

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

    Gebruikt otd_ok kolom als beschikbaar (config-driven) voor bepalen "te laat".
    """
    # Bepaal te late orders via otd_ok kolom of datumvergelijking
    if "otd_ok" in df.columns:
        te_laat_mask = df["otd_ok"].notna() & (df["otd_ok"].astype(float) == 0.0)
        te_laat = df[te_laat_mask].copy()
    elif "PODDeliveryDateShipment" in df.columns and "RequestedDeliveryDateFinal" in df.columns:
        pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
        req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        valid = pod.notna() & req.notna()
        te_laat = df[valid & (pod > req)].copy()
    else:
        return pd.DataFrame(columns=["DeliveryNumber", "root_cause", "root_cause_naam"])

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

    nummers = "\u2460\u2461\u2462\u2463\u2464\u2465"
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
