"""
CSV Sync Service
=================
Service ini bertanggung jawab menjaga file CSV di folder data/ tetap
sinkron dengan perubahan yang terjadi melalui website (input realisasi baru,
penambahan KPI baru, dll).

Strategi:
  - Setiap file CSV hanya berisi data untuk SATU kpi_id.
  - Nama file: <nama_slug>_kpi<kpi_id>.csv untuk KPI baru,
    atau file lama dikenali dengan scan isi (mencari kpi_id di baris data).
  - Semua operasi menggunakan file locking agar aman dari race condition.

Fungsi utama:
  - find_csv_for_kpi(kpi_id)    → cari path file CSV untuk kpi_id tertentu
  - append_realization(...)     → tambah baris baru ke CSV
  - update_realization(...)     → update baris yang sudah ada di CSV
  - delete_realization(...)     → hapus baris dari CSV
  - create_kpi_csv(...)         → buat file CSV baru untuk KPI baru
"""

import logging
import re
import threading
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ── Konstanta ─────────────────────────────────────────────────────────────── #
DATA_DIR = Path(__file__).parent.parent / "data"
CSV_COLUMNS = ["division_id", "kpi_id", "period_id", "year", "target", "realization"]

# File lock per kpi_id agar operasi concurrent tidak korupsi file
_locks: dict[int, threading.Lock] = {}
_locks_meta = threading.Lock()


def _get_lock(kpi_id: int) -> threading.Lock:
    """Ambil atau buat lock untuk kpi_id tertentu."""
    with _locks_meta:
        if kpi_id not in _locks:
            _locks[kpi_id] = threading.Lock()
        return _locks[kpi_id]


# ── Cache mapping kpi_id → Path ──────────────────────────────────────────── #
# Cache ini di-refresh setiap kali tidak ditemukan agar tidak stale
_kpi_path_cache: dict[int, Path] = {}
_cache_lock = threading.Lock()


def _scan_and_build_cache() -> dict[int, Path]:
    """
    Scan seluruh folder data/ dan bangun mapping kpi_id → filepath.
    Setiap file CSV diasumsikan hanya berisi satu kpi_id.
    """
    mapping: dict[int, Path] = {}
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for csv_file in DATA_DIR.glob("*.csv"):
        try:
            # Baca hanya kolom kpi_id, baris pertama data (bukan header)
            df = pd.read_csv(csv_file, usecols=["kpi_id"], nrows=1)
            if not df.empty:
                kpi_id = int(df["kpi_id"].iloc[0])
                mapping[kpi_id] = csv_file
        except Exception as e:
            logger.warning(f"csv_sync: skip {csv_file.name} — {e}")

    logger.debug(f"csv_sync: cache dibangun — {len(mapping)} KPI ditemukan")
    return mapping


def find_csv_for_kpi(kpi_id: int) -> Path | None:
    """
    Cari file CSV untuk kpi_id yang diberikan.
    Menggunakan cache; jika tidak ditemukan, scan ulang folder.

    Returns:
        Path ke file CSV, atau None jika tidak ditemukan.
    """
    global _kpi_path_cache

    with _cache_lock:
        # Cek cache dulu
        if kpi_id in _kpi_path_cache:
            path = _kpi_path_cache[kpi_id]
            if path.exists():
                return path
            # File sudah tidak ada, hapus dari cache
            del _kpi_path_cache[kpi_id]

        # Tidak ada di cache — scan ulang
        _kpi_path_cache = _scan_and_build_cache()
        return _kpi_path_cache.get(kpi_id)


def _invalidate_cache(kpi_id: int | None = None):
    """Hapus cache untuk kpi_id tertentu, atau seluruh cache jika None."""
    global _kpi_path_cache
    with _cache_lock:
        if kpi_id is None:
            _kpi_path_cache.clear()
        else:
            _kpi_path_cache.pop(kpi_id, None)


# ── Operasi CSV ───────────────────────────────────────────────────────────── #

def create_kpi_csv(kpi_id: int, kpi_name: str, division_id: int) -> Path:
    """
    Buat file CSV baru untuk KPI baru.
    File diberi nama berdasarkan slug kpi_name + kpi_id agar unik.

    Dipanggil saat: POST /admin/kpi (KPI baru ditambahkan)

    Returns:
        Path ke file CSV yang baru dibuat.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Buat slug dari nama KPI
    slug = re.sub(r"[^a-z0-9]+", "_", kpi_name.lower()).strip("_")
    slug = slug[:40]  # Batasi panjang nama file
    filename = f"{slug}_kpi{kpi_id}.csv"
    filepath = DATA_DIR / filename

    with _get_lock(kpi_id):
        if filepath.exists():
            logger.warning(f"csv_sync: file {filename} sudah ada — skip create")
            return filepath

        # Tulis header saja (belum ada data)
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(filepath, index=False)
        logger.info(f"csv_sync: ✓ File baru dibuat → {filename}")

    # Update cache
    with _cache_lock:
        _kpi_path_cache[kpi_id] = filepath

    return filepath


def append_realization(
    division_id: int,
    kpi_id: int,
    period_id: int,
    year: int,
    target: float,
    realization: float,
) -> bool:
    """
    Tambahkan baris baru ke file CSV yang sesuai.
    Jika kombinasi (kpi_id, period_id, year) sudah ada → update, bukan duplikat.

    Dipanggil saat: POST /admin/realization

    Returns:
        True jika berhasil, False jika gagal.
    """
    filepath = find_csv_for_kpi(kpi_id)
    if filepath is None:
        logger.error(f"csv_sync: file CSV untuk kpi_id={kpi_id} tidak ditemukan")
        return False

    new_row = {
        "division_id": division_id,
        "kpi_id":      kpi_id,
        "period_id":   period_id,
        "year":        year,
        "target":      target,
        "realization": realization,
    }

    with _get_lock(kpi_id):
        try:
            df = pd.read_csv(filepath)

            # Cek apakah kombinasi sudah ada (upsert)
            mask = (
                (df["kpi_id"]    == kpi_id)    &
                (df["period_id"] == period_id) &
                (df["year"]      == year)
            )
            if mask.any():
                # Update baris yang ada
                df.loc[mask, "target"]      = target
                df.loc[mask, "realization"] = realization
                df.to_csv(filepath, index=False)
                logger.info(
                    f"csv_sync: ✓ UPDATE {filepath.name} "
                    f"(kpi={kpi_id}, period={period_id}, year={year})"
                )
            else:
                # Append baris baru
                new_df = pd.DataFrame([new_row])
                df = pd.concat([df, new_df], ignore_index=True)
                df.to_csv(filepath, index=False)
                logger.info(
                    f"csv_sync: ✓ APPEND {filepath.name} "
                    f"(kpi={kpi_id}, period={period_id}, year={year})"
                )
            return True

        except Exception as e:
            logger.error(f"csv_sync: gagal append ke {filepath.name} — {e}", exc_info=True)
            return False


def update_realization(
    kpi_id: int,
    period_id: int,
    year: int,
    target: float | None = None,
    realization: float | None = None,
) -> bool:
    """
    Update nilai target dan/atau realization pada baris yang sudah ada di CSV.

    Dipanggil saat: PUT /admin/realization/{fact_id}

    Returns:
        True jika berhasil, False jika baris tidak ditemukan atau gagal.
    """
    filepath = find_csv_for_kpi(kpi_id)
    if filepath is None:
        logger.warning(f"csv_sync: file CSV untuk kpi_id={kpi_id} tidak ditemukan — skip update")
        return False

    with _get_lock(kpi_id):
        try:
            df = pd.read_csv(filepath)
            mask = (
                (df["kpi_id"]    == kpi_id)    &
                (df["period_id"] == period_id) &
                (df["year"]      == year)
            )

            if not mask.any():
                logger.warning(
                    f"csv_sync: baris tidak ditemukan di {filepath.name} "
                    f"(kpi={kpi_id}, period={period_id}, year={year})"
                )
                return False

            if target is not None:
                df.loc[mask, "target"] = target
            if realization is not None:
                df.loc[mask, "realization"] = realization

            df.to_csv(filepath, index=False)
            logger.info(
                f"csv_sync: ✓ UPDATE {filepath.name} "
                f"(kpi={kpi_id}, period={period_id}, year={year})"
            )
            return True

        except Exception as e:
            logger.error(f"csv_sync: gagal update {filepath.name} — {e}", exc_info=True)
            return False


def delete_realization(
    kpi_id: int,
    period_id: int,
    year: int,
) -> bool:
    """
    Hapus baris dari file CSV yang sesuai.

    Dipanggil saat: DELETE /admin/realization/{fact_id}

    Returns:
        True jika berhasil, False jika baris tidak ditemukan atau gagal.
    """
    filepath = find_csv_for_kpi(kpi_id)
    if filepath is None:
        logger.warning(f"csv_sync: file CSV untuk kpi_id={kpi_id} tidak ditemukan — skip delete")
        # Kembalikan True karena dari sisi DB sudah dihapus; CSV mungkin tidak ada
        return True

    with _get_lock(kpi_id):
        try:
            df = pd.read_csv(filepath)
            before = len(df)
            df = df[~(
                (df["kpi_id"]    == kpi_id)    &
                (df["period_id"] == period_id) &
                (df["year"]      == year)
            )]
            after = len(df)

            if before == after:
                logger.warning(
                    f"csv_sync: baris tidak ditemukan di {filepath.name} — tidak ada yang dihapus"
                )
                return True  # Tidak fatal; DB sudah dihapus

            df.to_csv(filepath, index=False)
            logger.info(
                f"csv_sync: ✓ DELETE dari {filepath.name} "
                f"(kpi={kpi_id}, period={period_id}, year={year})"
            )
            return True

        except Exception as e:
            logger.error(f"csv_sync: gagal delete dari {filepath.name} — {e}", exc_info=True)
            return False


def rebuild_csv_from_db(kpi_id: int, db) -> bool:
    """
    Rebuild file CSV untuk satu KPI berdasarkan data yang ada di database.
    Berguna untuk repair jika CSV dan DB tidak sinkron.

    Dipanggil dari: endpoint admin (opsional, untuk keperluan maintenance).
    """
    from sqlalchemy import text

    filepath = find_csv_for_kpi(kpi_id)
    if filepath is None:
        logger.warning(f"csv_sync: file CSV untuk kpi_id={kpi_id} tidak ditemukan")
        return False

    with _get_lock(kpi_id):
        try:
            rows = db.execute(text("""
                SELECT division_id, kpi_id, period_id, year, target, realization
                FROM fact_kpi_performance
                WHERE kpi_id = :kid
                ORDER BY year, period_id
            """), {"kid": kpi_id}).fetchall()

            df = pd.DataFrame(rows, columns=CSV_COLUMNS)
            df.to_csv(filepath, index=False)
            logger.info(
                f"csv_sync: ✓ REBUILD {filepath.name} — {len(df)} baris dari DB"
            )
            return True

        except Exception as e:
            logger.error(f"csv_sync: gagal rebuild {filepath.name} — {e}", exc_info=True)
            return False
