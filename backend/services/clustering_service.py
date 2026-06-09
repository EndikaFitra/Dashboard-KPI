"""
Clustering Service — K-Means++ Clustering untuk Divisi Sales Executive.

Mengambil data realisasi 3 indikator divisi Sales (Customer Baru, Quotation, MRR)
dari fact_kpi_performance, menjalankan clustering, menghitung metrik evaluasi,
dan menyimpan hasilnya ke tabel cluster_result & cluster_evaluation.

Metode:
  - Algoritma  : K-Means++ (KMeans, init='k-means++')
  - Normalisasi: StandardScaler (z-score)
  - Jumlah cluster: 5
  - Naming     : Mapping statis berdasarkan referensi cluster profiling
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
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
METHOD = "k-means++"


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

    # Guard: minimal harus ada cukup baris untuk N_CLUSTERS
    if len(df_wide) < N_CLUSTERS:
        raise ValueError(
            f"Data tidak cukup untuk clustering: hanya tersedia {len(df_wide)} observasi "
            f"dengan ketiga KPI lengkap (Customer Baru, Quotation, MRR), "
            f"minimal dibutuhkan {N_CLUSTERS}. "
            f"Pastikan data ketiga KPI Sales sudah terinput untuk periode yang sama."
        )

    logger.info(f"cluster: fetched {len(df_wide)} observations from database")
    return df_wide



# ── Fungsi 2: Normalisasi data ───────────────────────────────────────────── #

def _normalize_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    Normalisasi 3 kolom numerik menggunakan StandardScaler (z-score).

    Returns:
        Tuple of (DataFrame ternormalisasi, fitted scaler object)
    """
    numeric_cols = ["customer_baru", "quotation", "mrr"]
    scaler = StandardScaler()
    data_norm = pd.DataFrame(
        scaler.fit_transform(df[numeric_cols]),
        columns=numeric_cols,
    )
    return data_norm, scaler


# ── Fungsi 3: Jalankan clustering ─────────────────────────────────────────── #

def _run_clustering(data_norm: pd.DataFrame) -> np.ndarray:
    """
    Jalankan K-Means++ Clustering.

    Returns:
        labels array [0, 1, 2, ...]
    """
    kmeans_pp = KMeans(n_clusters=N_CLUSTERS, init="k-means++", n_init=10, random_state=42)
    labels = kmeans_pp.fit_predict(data_norm.values)

    logger.info(
        f"cluster: KMeans++ fitted — "
        f"n_clusters={N_CLUSTERS}, init=k-means++, "
        f"inertia={kmeans_pp.inertia_:.4f}, "
        f"cluster distribution={np.bincount(labels).tolist()}"
    )
    return labels, kmeans_pp


# ── Fungsi 4: Evaluasi kualitas clustering ────────────────────────────────── #

def _evaluate_clustering(
    data_norm: pd.DataFrame, labels: np.ndarray, kmeans_model: KMeans
) -> Dict[str, float]:
    """
    Hitung 3 metrik evaluasi K-Means++:
      1. Silhouette Score
      2. Davies-Bouldin Index
      3. BSS/TSS Ratio

    Returns:
        Dict dengan ketiga metrik.
    """
    values = data_norm.values

    # 1. Silhouette Score
    sil = silhouette_score(values, labels)

    # 2. Davies-Bouldin Index
    db_index = davies_bouldin_score(values, labels)

    # 3. BSS/TSS Ratio
    # WCSS (Within-Cluster Sum of Squares) diambil dari inertia
    wcss = kmeans_model.inertia_
    # Hitung titik pusat keseluruhan data
    global_mean = np.mean(values, axis=0)
    # Hitung TSS (Total Sum of Squares)
    tss = np.sum((values - global_mean) ** 2)
    # Hitung BSS (Between-Cluster Sum of Squares)
    bss = tss - wcss
    # Rasio BSS/TSS
    bss_tss = bss / tss if tss > 0 else 0.0

    metrics = {
        "silhouette_score": round(float(sil), 4),
        "davies_bouldin_index": round(float(db_index), 4),
        "bss_tss_ratio": round(float(bss_tss), 4),
    }

    logger.info(
        f"cluster: evaluation — silhouette={metrics['silhouette_score']}, "
        f"bss_tss={metrics['bss_tss_ratio']}, "
        f"davies_bouldin={metrics['davies_bouldin_index']}"
    )
    return metrics


# ── Fungsi 5: Cluster naming ─────────────────────────────────────────────── #

def _adaptive_cluster_naming(
    data_norm: pd.DataFrame, labels: np.ndarray
) -> Dict[int, str]:
    """
    Menggunakan mapping statis n=5 sesuai referensi cluster profiling K-Means++.

    Mapping berdasarkan profil debug server (business_labels):
      3: "High Efficiency"           (mrr tertinggi ~35.4M, quotation terendah)
      0: "High Activity Volume Drivers" (customer tertinggi ~14.1, quotation terendah)
      4: "Low Convertion Quality"    (cluster 0: moderate customer, quotation tinggi)
      1: "Small Tier"                (semua rendah)
      2: "Low Efficiency"            (customer & quotation tinggi, mrr terendah)
    """
    mapping = {
        0: "High Activity Volume Drivers",
        1: "Small Tier",
        2: "Low Efficiency",
        3: "High Efficiency",
        4: "Low Convertion Quality",
    }

    result = {}
    for cluster_id in range(N_CLUSTERS):
        result[cluster_id] = mapping.get(cluster_id, f"Cluster {cluster_id}")

    logger.info(f"cluster: static naming (n=5, k-means++) — {result}")
    return result


# ── Fungsi 6: Orkestrasi utama + simpan ke DB ────────────────────────────── #

def run_full_clustering(db: Session) -> Dict:
    """
    Jalankan pipeline clustering lengkap dan simpan hasilnya ke database.

    Alur:
      1. Fetch data Sales dari fact_kpi_performance
      2. Normalisasi dengan StandardScaler (z-score)
      3. Jalankan K-Means++ (n=5, init='k-means++', n_init=10)
      4. Hitung metrik evaluasi (Silhouette, BSS/TSS, Davies-Bouldin)
      5. Tentukan nama cluster sesuai mapping statis
      6. Hapus data lama, simpan data baru ke cluster_result & cluster_evaluation

    Returns:
        Dict berisi evaluation, data_table, scatter_2d (langsung bisa dikirim ke frontend)
    """
    logger.info("cluster: starting full clustering pipeline (K-Means++)...")

    # 1. Fetch data
    data_raw = _fetch_sales_data(db)

    # 2. Normalize
    data_norm, scaler = _normalize_data(data_raw)

    # 3. Cluster
    labels, kmeans_model = _run_clustering(data_norm)

    # 4. Evaluate
    metrics = _evaluate_clustering(data_norm, labels, kmeans_model)

    # 5. Naming
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
        davies_bouldin_index=metrics["davies_bouldin_index"],
        n_clusters=N_CLUSTERS,
        method=METHOD,
        n_observations=len(data_raw),
        computed_at=now,
    )
    db.add(eval_row)

    db.commit()
    logger.info(
        f"cluster: ✓ pipeline complete (K-Means++) — "
        f"{len(data_raw)} observations, {N_CLUSTERS} clusters saved to database"
    )

    # 7. Build response
    return _build_response(db)


# ── Fungsi 7: Baca hasil dari database ────────────────────────────────────── #

def get_cluster_results(db: Session) -> Dict:
    """
    Baca hasil clustering yang tersimpan di database.
    Jika belum ada data, otomatis jalankan run_full_clustering() terlebih dahulu.

    Returns:
        Dict berisi evaluation, data_table, scatter_3d, scatter_2d, cluster_descriptions
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
        "davies_bouldin_index": eval_row.davies_bouldin_index,
        "n_clusters": eval_row.n_clusters,
        "method": eval_row.method,
        "n_observations": eval_row.n_observations,
        "computed_at": eval_row.computed_at.isoformat(),
    }

    # Build data_table (data asli + cluster name + label periode)
    data_table = [
        {
            "observation_index": r.observation_index,
            "periode": f"{r.year}-{r.quarter}",   # e.g. "2016-Q1"
            "year": r.year,
            "quarter": r.quarter,
            "customer_baru": r.customer_baru,
            "quotation": r.quotation,
            "mrr": r.mrr,
            "cluster_name": r.cluster_name,
        }
        for r in results
    ]

    results_ordered = sorted(results, key=lambda r: r.observation_index)
    raw_values = np.array([
        [r.customer_baru, r.quotation, r.mrr]
        for r in results_ordered
    ])

    if len(raw_values) > 1:
        from sklearn.preprocessing import StandardScaler as _SS
        _scaler = _SS()
        X_scaled_fresh = _scaler.fit_transform(raw_values)

        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(X_scaled_fresh)
        explained_variance = pca.explained_variance_ratio_ * 100

        pca_result[:, 1] *= -1
    else:
        pca_result = np.zeros((len(raw_values), 2))
        explained_variance = [0, 0]

    scatter_2d = [
        {
            "pca_x": float(pca_result[i][0]),
            "pca_y": float(pca_result[i][1]),
            "periode": f"{r.year}-{r.quarter}",
            "customer_baru_norm": float(r.customer_baru_norm),
            "quotation_norm": float(r.quotation_norm),
            "mrr_norm": float(r.mrr_norm),
            "cluster_name": r.cluster_name,
        }
        for i, r in enumerate(results_ordered)
    ]

    # Cluster descriptions (template — dapat diedit di ClusterPage.tsx, konstanta CLUSTER_DESCRIPTIONS)
    cluster_descriptions = {
        "High Efficiency": (
            "Cluster ini menghasilkan MRR paling tinggi dengan sedikit quotation yang dikirimkan. Hal ini menunjukkan bahwa, kesepakatan nilai kontrak yang dihasilkan sangat tinggi."

        ),
        "High Activity Volume Drivers": (
            "Cluster ini menghasilkan MRR dan quotation yang dikirimkan tertinggi kedua. Hal ini menunjukkan stabilitas kinerja dengan tingginya MRR yang didapatkan."

        ),
        "Low Convertion Quality": (
            "Cluster ini mengirimkan quotation yang sama seperti pada klaster 'High Efficiency' dan mendapatkan customer baru paling banyak. Tetapi MRR yang dihasilkan tidak sebanyak pada klaster 'High Efficiency'. Hal ini dapat disebabkan karena nilai kesepakatan kontrak yang dihasilkan rendah."

        ),
        "Small Tier": (
            "Cluster ini menghasilkan MRR terendah kedua meskipun quotation yang dikirimkan cukup banyak. Hal ini dapat disebabkan oleh rendahnya tingkat kesepaktan yang terjadi."

        ),
        "Low Efficiency": (
            "Cluster ini menghasilkan nilai MRR yang paling rendah meskipun paling banyak mengirimkan quotation. Jumlah customer baru yang diperoleh cukup tinggi. Rendahnya MRR yang diperoleh dapat disebabkan karena nilai kesepakatan kontrak rendah dan prospek pelanggan kurang bagus."

        ),
    }

    return {
        "evaluation": evaluation,
        "data_table": data_table,
        "scatter_2d": scatter_2d,
        "pca_variance": {
            "pc1": float(explained_variance[0]),
            "pc2": float(explained_variance[1])
        },
        "cluster_descriptions": cluster_descriptions,
    }
