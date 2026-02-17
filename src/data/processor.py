"""KPI-berekeningen en aggregaties."""

import pandas as pd

from src.utils.constants import KPI_IDS, KPI_NAMEN, KPI_STAPPEN


def bereken_kpi_scores(df: pd.DataFrame) -> dict[str, float]:
    """Berekent percentage OK per KPI-stap."""
    scores = {}
    for kpi_id in KPI_IDS:
        if kpi_id in df.columns:
            scores[kpi_id] = df[kpi_id].mean() * 100
        else:
            scores[kpi_id] = 0.0
    return scores


def bereken_otd(df: pd.DataFrame) -> float:
    """Berekent overall On-Time Delivery %."""
    if "gewenste_leverdatum" not in df.columns or "werkelijke_leverdatum" not in df.columns:
        return 0.0
    op_tijd = df["werkelijke_leverdatum"] <= df["gewenste_leverdatum"]
    return op_tijd.mean() * 100


def bereken_root_causes(df: pd.DataFrame) -> pd.DataFrame:
    """Bepaalt voor elke te late order de eerste falende stap (root cause).
    Retourneert DataFrame met kolommen: ordernummer, root_cause, root_cause_naam.
    """
    # Filter te late orders
    te_laat = df[df["werkelijke_leverdatum"] > df["gewenste_leverdatum"]].copy()

    if te_laat.empty:
        return pd.DataFrame(columns=["ordernummer", "root_cause", "root_cause_naam"])

    def eerste_faal(row):
        for stap in KPI_STAPPEN:
            kpi_id = stap["id"]
            if kpi_id in row.index and not row[kpi_id]:
                return kpi_id
        return "onbekend"

    te_laat["root_cause"] = te_laat.apply(eerste_faal, axis=1)
    te_laat["root_cause_naam"] = te_laat["root_cause"].map(
        lambda x: KPI_NAMEN.get(x, "Onbekend")
    )

    return te_laat[["ordernummer", "root_cause", "root_cause_naam"]]


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
    Voor elke stap: hoeveel orders falen HIER (eerste faal).
    """
    rc = bereken_root_causes(df)
    totaal_orders = len(df)
    te_laat = len(rc)
    op_tijd = totaal_orders - te_laat

    rijen = []

    # Start: totaal orders
    rijen.append({"stap": "Totaal Orders", "waarde": totaal_orders, "type": "totaal"})

    # Per stap: hoeveel falen hier
    for stap in KPI_STAPPEN:
        naam = stap["naam"]
        kpi_id = stap["id"]
        aantal_faal = len(rc[rc["root_cause"] == kpi_id])
        rijen.append({"stap": f"① {naam}" if stap["nummer"] == 1 else f"{'②③④⑤⑥⑦'[stap['nummer']-2]} {naam}",
                       "waarde": -aantal_faal, "type": "faal"})

    # Eind: op tijd geleverd
    rijen.append({"stap": "Op Tijd Geleverd", "waarde": op_tijd, "type": "ok"})

    return pd.DataFrame(rijen)


def groepeer_per_periode(df: pd.DataFrame, periode_kolom: str = "week") -> pd.DataFrame:
    """Groepeert KPI-scores per periode (week of maand)."""
    if periode_kolom not in df.columns:
        return pd.DataFrame()

    resultaat = df.groupby(periode_kolom)[KPI_IDS].mean() * 100
    resultaat = resultaat.reset_index()
    return resultaat
