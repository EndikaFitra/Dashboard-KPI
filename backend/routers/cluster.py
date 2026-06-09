"""
Cluster Router — Agglomerative K-Means++ Clustering Endpoints

GET  /cluster/results   → Ambil hasil clustering
POST /cluster/recompute → Re-compute clustering dari data terbaru
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from services.clustering_service import get_cluster_results, run_full_clustering

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/results")
def cluster_results(db: Session = Depends(get_db)):
    """
    Ambil hasil clustering yang tersimpan di database.

    Jika belum pernah di-compute, otomatis jalankan clustering terlebih dahulu.
    Response berisi: evaluation metrics, data table, scatter 3D points,
    dan template deskripsi cluster.
    """
    logger.info("GET /cluster/results")
    try:
        return get_cluster_results(db)
    except ValueError as e:
        # Data Sales tidak cukup untuk clustering
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster results error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
def cluster_recompute(db: Session = Depends(get_db)):
    """
    Paksa re-compute clustering dari data terbaru di database.

    Dipanggil secara otomatis oleh admin router saat data Sales berubah,
    atau bisa dipanggil manual untuk refresh.
    """
    logger.info("POST /cluster/recompute")
    try:
        result = run_full_clustering(db)
        return {
            "status": "success",
            "message": "Clustering recomputed successfully",
            "n_observations": result["evaluation"]["n_observations"],
            "n_clusters": result["evaluation"]["n_clusters"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cluster recompute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
