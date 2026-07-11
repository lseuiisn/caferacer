"""Temporarily verify candidate cafe addresses with TMAP geocoding.

This script deliberately prints results only. Do not save TMAP-derived coordinates as permanent
cafe data without confirming the provider's current retention and licensing conditions.
"""

import argparse
import asyncio
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.integrations.tmap import TmapClient, TmapError


@dataclass(frozen=True)
class CafeCandidate:
    name: str
    address: str
    source_url: str


def read_candidates(path: Path) -> list[CafeCandidate]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))
    if not rows:
        return []
    first_cell = rows[0][0].strip() if rows[0] else ""
    data_rows = rows[1:] if first_cell in {"카페명", "name"} else rows
    candidates = []
    for row_number, row in enumerate(data_rows, start=2 if data_rows is not rows else 1):
        if len(row) < 3:
            raise ValueError(f"Row {row_number} must have name, address, and source URL")
        candidates.append(CafeCandidate(name=row[0].strip(), address=row[1].strip(), source_url=row[2].strip()))
    return candidates


def coordinates_from_source_url(source_url: str) -> tuple[float, float] | None:
    query = parse_qs(urlparse(source_url).query)
    if not query.get("lat") or not query.get("lng"):
        return None
    return float(query["lat"][0]), float(query["lng"][0])


async def verify(path: Path) -> None:
    client = TmapClient()
    candidates = read_candidates(path)
    print(f"검증 대상: {len(candidates)}개")
    for candidate in candidates:
        source_coordinates = coordinates_from_source_url(candidate.source_url)
        try:
            geocoded = await client.geocode_full_address(candidate.address)
            source_text = (
                f"URL 좌표 {source_coordinates[0]:.7f}, {source_coordinates[1]:.7f}"
                if source_coordinates
                else "URL 좌표 없음"
            )
            print(
                f"[확인] {candidate.name}: {geocoded.latitude:.7f}, {geocoded.longitude:.7f} "
                f"({source_text})"
            )
        except TmapError as error:
            print(f"[실패] {candidate.name}: {error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="카페명,주소,출처 URL 형식의 UTF-8 CSV")
    arguments = parser.parse_args()
    asyncio.run(verify(arguments.path))
