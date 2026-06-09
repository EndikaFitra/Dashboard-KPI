"""
Migrate cluster_evaluation table:
- Drop old column: cophenetic_corr
- Add new column: davies_bouldin_index
- Clear stale data so it gets recomputed on next API call
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE cluster_evaluation DROP COLUMN IF EXISTS cophenetic_corr'))
    print('Dropped cophenetic_corr')

    conn.execute(text('ALTER TABLE cluster_evaluation ADD COLUMN IF NOT EXISTS davies_bouldin_index FLOAT'))
    print('Added davies_bouldin_index')

    # Hapus data lama supaya recompute otomatis saat GET /cluster/results
    conn.execute(text('DELETE FROM cluster_evaluation'))
    conn.execute(text('DELETE FROM cluster_result'))
    conn.commit()
    print('Cleared old cluster data — will recompute on next GET /cluster/results')
