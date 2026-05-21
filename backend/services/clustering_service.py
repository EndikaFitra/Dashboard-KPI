"""
Clustering Service — Agglomerative Hierarchical Clustering untuk Sales KPI.

Mengambil data realisasi 3 indikator divisi Sales (Customer Baru, Quotation, MRR)
dari fact_kpi_performance, menjalankan clustering, menghitung metrik evaluasi,
dan menyimpan hasilnya ke tabel cluster_result & cluster_evaluation.

Metode:
  - Algoritma  : Agglomerative Hierarchical Clustering
  - Linkage    : Ward (meminimalkan kenaikan varians total)
  - Normalisasi: MinMaxScaler (range 0–1)
  - Jumlah cluster: 6
  - Naming     : Adaptif berdasarkan profil rata-rata cluster

Referensi: kode notebook Python milik user (ARIMA-style integration).
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, cophenet
from scipy.spatial.distance import pdist
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy.orm import Session

from models.cluster import ClusterResult, ClusterEvaluation

logger = logging.getLogger(__name__)

# ── Konstanta ─────────────────────────────────────────────────────────────── #

# KPI IDs milik divisi Sales Executive
KPI_CUSTOMER_BARU = 9
KPI_QUOTATION = 10
KPI_MRR = 8
SALES_DIVISION_ID = 3

# Mapping period_id → quarter label (sama dengan forecasting_service.py)
PERIOD_TO_QUARTER = {13: "Q1", 14: "Q2", 15: "Q3", 16: "Q4"}

N_CLUSTERS = 5
LINKAGE_METHOD = "average"


# ── Fungsi 1: Ambil data Sales dari database ─────────────────────────────── #

def _fetch_sales_data(db: Session) -> pd.DataFrame:
    """
    Query data realisasi 3 KPI Sales dari fact_kpi_performance.
    Pivot ke format wide: 1 baris = 1 observasi (year × quarter).

    Returns:
        DataFrame dengan kolom: year, quarter, customer_baru, quotation, mrr
        Diurutkan secara kronologis. Jumlah baris = jumlah quarter yang ada data.
    """
    from sqlalchemy import text

    sql = text("""
        SELECT
            f.year,
            f.period_id,
            f.kpi_id,
            f.realization
        FROM fact_kpi_performance f
        WHERE f.division_id = :div_id
          AND f.kpi_id IN (:kpi_cb, :kpi_quo, :kpi_mrr)
          AND f.period_id IN (13, 14, 15, 16)
        ORDER BY f.year, f.period_id, f.kpi_id
    """)

    rows = db.execute(sql, {
        "div_id": SALES_DIVISION_ID,
        "kpi_cb": KPI_CUSTOMER_BARU,
        "kpi_quo": KPI_QUOTATION,
        "kpi_mrr": KPI_MRR,
    }).fetchall()

    if not rows:
        raise ValueError("Tidak ada data Sales KPI di database untuk clustering.")

    # Bangun DataFrame long-format
    records = []
    for row in rows:
        q_label = PERIOD_TO_QUARTER.get(row.period_id)
        if q_label is None:
            continue
        records.append({
            "year": row.year,
            "quarter": q_label,
            "kpi_id": row.kpi_id,
            "realization": float(row.realization),
        })

    df_long = pd.DataFrame(records)

    # Map kpi_id ke nama kolom
    kpi_name_map = {
        KPI_CUSTOMER_BARU: "customer_baru",
        KPI_QUOTATION: "quotation",
        KPI_MRR: "mrr",
    }
    df_long["kpi_name"] = df_long["kpi_id"].map(kpi_name_map)

    # Pivot: dari long ke wide
    df_wide = df_long.pivot_table(
        index=["year", "quarter"],
        columns="kpi_name",
        values="realization",
        aggfunc="first",  # 1 nilai per kombinasi
    ).reset_index()

    # Flatten column names
    df_wide.columns.name = None

    # Urutkan kronologis
    quarter_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    df_wide["_q_order"] = df_wide["quarter"].map(quarter_order)
    df_wide = df_wide.sort_values(["year", "_q_order"]).reset_index(drop=True)
    df_wide = df_wide.drop(columns=["_q_order"])

    # Drop baris yang tidak lengkap (kurang dari 3 KPI)
    df_wide = df_wide.dropna(subset=["customer_baru", "quotation", "mrr"]).reset_index(drop=True)

    logger.info(f"cluster: fetched {len(df_wide)} observations from database")
    return df_wide


# ── Fungsi 2: Normalisasi data ───────────────────────────────────────────── #

def _normalize_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, MinMaxScaler]:
    """
    Normalisasi 3 kolom numerik ke rentang 0–1 menggunakan MinMaxScaler.

    Returns:
        Tuple of (DataFrame ternormalisasi, fitted scaler object)
    """
    numeric_cols = ["customer_baru", "quotation", "mrr"]
    scaler = MinMaxScaler()
    data_norm = pd.DataFrame(
        scaler.fit_transform(df[numeric_cols]),
        columns=numeric_cols,
    )
    return data_norm, scaler


# ── Fungsi 3: Jalankan clustering ─────────────────────────────────────────── #

def _run_clustering(data_norm: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Jalankan Agglomerative Hierarchical Clustering dengan Ward linkage.

    Returns:
        Tuple of (labels array [0,1,2,...], linkage matrix Z)
    """
    # Hitung linkage matrix untuk evaluasi cophenetic
    Z = linkage(data_norm.values, method=LINKAGE_METHOD)

    # Fit model clustering
    model = AgglomerativeClustering(n_clusters=N_CLUSTERS, linkage=LINKAGE_METHOD)
    labels = model.fit_predict(data_norm.values)

    logger.info(
        f"cluster: AgglomerativeClustering fitted — "
        f"n_clusters={N_CLUSTERS}, method={LINKAGE_METHOD}, "
        f"cluster distribution={np.bincount(labels).tolist()}"
    )
    return labels, Z


# ── Fungsi 4: Evaluasi kualitas clustering ────────────────────────────────── #

def _evaluate_clustering(
    data_norm: pd.DataFrame, labels: np.ndarray, Z: np.ndarray
) -> Dict[str, float]:
    """
    Hitung 3 metrik evaluasi:
      1. Cophenetic Correlation Coefficient
      2. Silhouette Score
      3. BSS/TSS Ratio

    Returns:
        Dict dengan ketiga metrik.
    """
    values = data_norm.values

    # 1. Cophenetic Correlation
    c, _ = cophenet(Z, pdist(values))

    # 2. Silhouette Score
    sil = silhouette_score(values, labels)

    # 3. BSS/TSS Ratio
    global_mean = np.mean(values, axis=0)
    TSS = np.sum((values - global_mean) ** 2)

    WSS = 0.0
    for cluster_id in range(N_CLUSTERS):
        cluster_mask = labels == cluster_id
        if not np.any(cluster_mask):
            continue
        cluster_data = values[cluster_mask]
        cluster_mean = np.mean(cluster_data, axis=0)
        WSS += np.sum((cluster_data - cluster_mean) ** 2)

    BSS = TSS - WSS
    bss_tss = BSS / TSS if TSS > 0 else 0.0

    metrics = {
        "cophenetic_corr": round(float(c), 4),
        "silhouette_score": round(float(sil), 4),
        "bss_tss_ratio": round(float(bss_tss), 4),
    }

    logger.info(
        f"cluster: evaluation — silhouette={metrics['silhouette_score']}, "
        f"bss_tss={metrics['bss_tss_ratio']}, cophenetic={metrics['cophenetic_corr']}"
    )
    return metrics


# ── Fungsi 5: Adaptive cluster naming ─────────────────────────────────────── #

def _adaptive_cluster_naming(
    data_norm: pd.DataFrame, labels: np.ndarray
) -> Dict[int, str]:
    """
    Menggunakan mapping statis n=5 sesuai referensi.
    """
    mapping = {
        0 : 'Peak Revenue & Premium Efficiency',
        1 : 'Core Growth & Stable Acquisition',
        2 : 'Stagnant Acquisition & Slow Down',
        3 : 'Low-Yield Operational',
        4 : 'Hyper-Acquisition & Market Penetration'
    }

    result = {}
    for cluster_id in range(N_CLUSTERS):
        result[cluster_id] = mapping.get(cluster_id, f"Cluster {cluster_id}")

    logger.info(f"cluster: static naming (n=5) — {result}")
    return result


# ── Fungsi 6: Orkestrasi utama + simpan ke DB ────────────────────────────── #

def run_full_clustering(db: Session) -> Dict:
    """
    Jalankan pipeline clustering lengkap dan simpan hasilnya ke database.

    Alur:
      1. Fetch data Sales dari fact_kpi_performance
      2. Normalisasi dengan MinMaxScaler
      3. Jalankan Agglomerative Clustering (Ward, n=3)
      4. Hitung metrik evaluasi (Silhouette, BSS/TSS, Cophenetic)
      5. Tentukan nama cluster secara adaptif
      6. Hapus data lama, simpan data baru ke cluster_result & cluster_evaluation

    Returns:
        Dict berisi evaluation, data_table, scatter_3d (langsung bisa dikirim ke frontend)
    """
    logger.info("cluster: starting full clustering pipeline...")

    # 1. Fetch data
    data_raw = _fetch_sales_data(db)

    # 2. Normalize
    data_norm, scaler = _normalize_data(data_raw)

    # 3. Cluster
    labels, Z = _run_clustering(data_norm)

    # 4. Evaluate
    metrics = _evaluate_clustering(data_norm, labels, Z)

    # 5. Adaptive naming
    name_mapping = _adaptive_cluster_naming(data_norm, labels)

    # 6. Simpan ke database
    now = datetime.utcnow()

    # 6a. Hapus data lama
    db.query(ClusterResult).delete()
    db.query(ClusterEvaluation).delete()

    # 6b. Insert cluster_result (satu baris per observasi)
    for i in range(len(data_raw)):
        cluster_id = int(labels[i])
        result_row = ClusterResult(
            observation_index=i,
            year=int(data_raw.iloc[i]["year"]),
            quarter=str(data_raw.iloc[i]["quarter"]),
            customer_baru=float(data_raw.iloc[i]["customer_baru"]),
            quotation=float(data_raw.iloc[i]["quotation"]),
            mrr=float(data_raw.iloc[i]["mrr"]),
            customer_baru_norm=float(data_norm.iloc[i]["customer_baru"]),
            quotation_norm=float(data_norm.iloc[i]["quotation"]),
            mrr_norm=float(data_norm.iloc[i]["mrr"]),
            cluster_id=cluster_id,
            cluster_name=name_mapping[cluster_id],
            computed_at=now,
        )
        db.add(result_row)

    # 6c. Insert cluster_evaluation
    eval_row = ClusterEvaluation(
        silhouette_score=metrics["silhouette_score"],
        bss_tss_ratio=metrics["bss_tss_ratio"],
        cophenetic_corr=metrics["cophenetic_corr"],
        n_clusters=N_CLUSTERS,
        method=LINKAGE_METHOD,
        n_observations=len(data_raw),
        computed_at=now,
    )
    db.add(eval_row)

    db.commit()
    logger.info(
        f"cluster: ✓ pipeline complete — "
        f"{len(data_raw)} observations, {N_CLUSTERS} clusters saved to database"
    )

    # 7. Build response (sama format dengan get_cluster_results)
    return _build_response(db)


# ── Fungsi 7: Baca hasil dari database ────────────────────────────────────── #

def get_cluster_results(db: Session) -> Dict:
    """
    Baca hasil clustering yang tersimpan di database.
    Jika belum ada data, otomatis jalankan run_full_clustering() terlebih dahulu.

    Returns:
        Dict berisi evaluation, data_table, scatter_3d, cluster_descriptions
    """
    # Cek apakah ada data evaluasi
    eval_row = db.query(ClusterEvaluation).order_by(
        ClusterEvaluation.computed_at.desc()
    ).first()

    if eval_row is None:
        # Belum pernah di-compute — jalankan dulu
        logger.info("cluster: no cached results found, running full clustering...")
        return run_full_clustering(db)

    return _build_response(db)


def _build_response(db: Session) -> Dict:
    """
    Bangun response dict dari data yang tersimpan di database.
    Format ini yang dikirim ke frontend.
    """
    # Query evaluation
    eval_row = db.query(ClusterEvaluation).order_by(
        ClusterEvaluation.computed_at.desc()
    ).first()

    # Query semua cluster results
    results = db.query(ClusterResult).order_by(
        ClusterResult.observation_index
    ).all()

    # Build evaluation dict
    evaluation = {
        "silhouette_score": eval_row.silhouette_score,
        "bss_tss_ratio": eval_row.bss_tss_ratio,
        "cophenetic_corr": eval_row.cophenetic_corr,
        "n_clusters": eval_row.n_clusters,
        "method": eval_row.method,
        "n_observations": eval_row.n_observations,
        "computed_at": eval_row.computed_at.isoformat(),
    }

    # Build data_table (data asli + cluster name)
    data_table = [
        {
            "observation_index": r.observation_index,
            "year": r.year,
            "quarter": r.quarter,
            "customer_baru": r.customer_baru,
            "quotation": r.quotation,
            "mrr": r.mrr,
            "cluster_name": r.cluster_name,
        }
        for r in results
    ]

    # Build scatter_3d (data ternormalisasi + cluster name)
    scatter_3d = [
        {
            "customer_baru_norm": r.customer_baru_norm,
            "quotation_norm": r.quotation_norm,
            "mrr_norm": r.mrr_norm,
            "cluster_name": r.cluster_name,
        }
        for r in results
    ]

    # Cluster descriptions (template terstruktur)
    cluster_descriptions = {
        "Mass Acquisition Phase": (
            "Cluster ini ditandai dengan tingkat akuisisi customer baru yang tinggi.\n\n"
            "Karakteristik utama meliputi:\n"
            "• Volume customer baru di atas rata-rata\n"
            "• Quotation conversion rate bervariasi\n"
            "• MRR yang kompetitif\n\n"
            "Interpretasi bisnis: [Silakan diisi oleh pengguna]"
        ),
        "Premium-Focus Phase": (
            "Cluster ini ditandai dengan fokus pada customer bernilai tinggi.\n\n"
            "Karakteristik utama meliputi:\n"
            "• Volume customer baru relatif rendah\n"
            "• MRR (Monthly Recurring Revenue) paling tinggi\n"
            "• Quotation conversion rate tinggi\n\n"
            "Interpretasi bisnis: [Silakan diisi oleh pengguna]"
        ),
        "Low-Conversion Phase": (
            "Cluster ini ditandai dengan performa keseluruhan yang rendah.\n\n"
            "Karakteristik utama meliputi:\n"
            "• Volume customer baru paling rendah\n"
            "• MRR di bawah rata-rata\n"
            "• Quotation conversion rate rendah\n\n"
            "Interpretasi bisnis: [Silakan diisi oleh pengguna]"
        ),
    }

    return {
        "evaluation": evaluation,
        "data_table": data_table,
        "scatter_3d": scatter_3d,
        "cluster_descriptions": cluster_descriptions,
    }
