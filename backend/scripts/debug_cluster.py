"""
Debug: bandingkan nilai PC2 server vs lokal user baris per baris.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
sql = text("""
    SELECT f.year, f.period_id, f.kpi_id, f.realization
    FROM fact_kpi_performance f
    WHERE f.division_id = 3
      AND f.kpi_id IN (9, 10, 8)
      AND f.period_id IN (13, 14, 15, 16)
    ORDER BY f.year, f.period_id, f.kpi_id
""")
rows = db.execute(sql).fetchall()
period_map = {13: "Q1", 14: "Q2", 15: "Q3", 16: "Q4"}
kpi_map = {9: "customer_baru", 10: "quotation", 8: "mrr"}
records = []
for r in rows:
    q = period_map.get(r.period_id)
    if q:
        records.append({"year": r.year, "quarter": q,
                        "kpi_id": r.kpi_id, "realization": float(r.realization)})
df_long = pd.DataFrame(records)
df_long["kpi_name"] = df_long["kpi_id"].map(kpi_map)
df_wide = df_long.pivot_table(
    index=["year", "quarter"], columns="kpi_name",
    values="realization", aggfunc="first"
).reset_index()
df_wide.columns.name = None
q_ord = {"Q1":1,"Q2":2,"Q3":3,"Q4":4}
df_wide["_q"] = df_wide["quarter"].map(q_ord)
df_wide = df_wide.sort_values(["year","_q"]).reset_index(drop=True).drop(columns=["_q"])
df_wide = df_wide.dropna(subset=["customer_baru","quotation","mrr"]).reset_index(drop=True)
db.close()

# PCA persis seperti notebook: StandardScaler fresh -> PCA no sign fix
X = df_wide[["customer_baru","quotation","mrr"]].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

print("PCA components (eigenvectors):")
print("  PC1:", np.round(pca.components_[0], 6).tolist())
print("  PC2:", np.round(pca.components_[1], 6).tolist())

# Data PCA lokal user (diisi manual dari gambar 3 & 4)
local_pca2 = [
    -1.047282, 0.843876, 0.792063, -0.043117, 1.603736,
    1.830276, -1.046835, -0.587594, 0.058863, 1.279744,
    -1.115644, 0.184353, -1.793564, 0.441143, -0.093612,
    1.211431, -0.319338, 0.076587, -0.998212, 0.627224,
    0.768085, 0.304864, -0.653807, -1.139998, 1.009961,
    2.012817, 0.410015, 0.739493, -0.602938, -0.999835,
    -0.362252, 0.423906, -1.735235, -0.211758, 0.236879,
    0.470905, 1.645170, -1.747460, -0.816246, -0.103090,
    -0.553573
]

print("\nPerbandingan PC2: server RAW vs lokal user:")
print(f"{'idx':>4} {'server_pc2':>12} {'local_pc2':>12} {'ratio':>8} {'negated?':>10}")
for i in range(41):
    sv = X_pca[i, 1]
    lc = local_pca2[i]
    ratio = sv / lc if abs(lc) > 1e-9 else float('nan')
    neg = "YES" if abs(ratio + 1.0) < 0.01 else "NO"
    print(f"  {i:>2}  {sv:>12.6f}  {lc:>12.6f}  {ratio:>8.4f}  {neg}")

print("\nApakah semua PC2 server = -1 * local?")
all_neg = all(abs(X_pca[i,1] / local_pca2[i] + 1.0) < 0.02 for i in range(41) if abs(local_pca2[i]) > 0.1)
print("  Hasil:", all_neg)

print("\nPC2 setelah NEGASI server (= local?):")
for i in range(5):
    sv_neg = -X_pca[i, 1]
    lc = local_pca2[i]
    diff = abs(sv_neg - lc)
    print(f"  obs {i}: negated_server={sv_neg:.6f}  local={lc:.6f}  diff={diff:.8f}")
