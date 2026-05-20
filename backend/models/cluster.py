"""
Cluster Models — Tabel untuk menyimpan hasil clustering Sales KPI.

Tabel:
  - cluster_result     : Hasil cluster per observasi (41+ baris)
  - cluster_evaluation : Metrik evaluasi clustering (1 baris per run)

Digunakan oleh: services/clustering_service.py
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base


class ClusterResult(Base):
    """
    Menyimpan hasil cluster untuk setiap observasi (baris data).

    Setiap baris merepresentasikan satu kombinasi year × quarter
    dengan nilai asli (sebelum normalisasi), nilai ternormalisasi,
    dan label cluster hasil Agglomerative Hierarchical Clustering.
    """
    __tablename__ = "cluster_result"

    id                = Column(Integer, primary_key=True, index=True)
    observation_index = Column(Integer, nullable=False)
    year              = Column(Integer, nullable=False)
    quarter           = Column(String(2), nullable=False)       # Q1, Q2, Q3, Q4
    # Data asli (sebelum normalisasi)
    customer_baru     = Column(Float, nullable=False)
    quotation         = Column(Float, nullable=False)
    mrr               = Column(Float, nullable=False)
    # Data ternormalisasi (MinMaxScaler, range 0–1)
    customer_baru_norm = Column(Float, nullable=False)
    quotation_norm     = Column(Float, nullable=False)
    mrr_norm           = Column(Float, nullable=False)
    # Hasil clustering
    cluster_id        = Column(Integer, nullable=False)         # 0, 1, atau 2
    cluster_name      = Column(String(50), nullable=False)      # Nama adaptif
    computed_at       = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClusterEvaluation(Base):
    """
    Menyimpan metrik evaluasi kualitas clustering.

    Hanya 1 baris aktif pada satu waktu (di-replace setiap re-compute).
    Metrik:
      - silhouette_score : kualitas pemisahan cluster (-1 s/d 1)
      - bss_tss_ratio    : proporsi varians yang dijelaskan cluster (0–1)
      - cophenetic_corr  : validitas representasi dendrogram (0–1)
    """
    __tablename__ = "cluster_evaluation"

    id               = Column(Integer, primary_key=True, index=True)
    silhouette_score = Column(Float, nullable=False)
    bss_tss_ratio    = Column(Float, nullable=False)
    cophenetic_corr  = Column(Float, nullable=False)
    n_clusters       = Column(Integer, nullable=False, default=3)
    method           = Column(String(20), nullable=False, default="ward")
    n_observations   = Column(Integer, nullable=False)
    computed_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
