#!/usr/bin/env python3
"""Build derived indexes without writing to source transcripts (stdlib only)."""

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
TOPICS = "clients contracts payments sales pricing partnerships business_formation intellectual_property employment taxes disputes risk_management marketing operations financing".split()
SITUATIONS = "client_nonpayment scope_creep client_dispute refund_request partner_dispute business_startup contract_negotiation ip_infringement employee_issue tax_issue lawsuit_threat business_sale".split()
ENTITIES = "small_business consulting_business creative_business ecommerce_business nonprofit".split()
STAGES = "startup operating unknown".split()
ENUMS = {
    "rf_applicability": "unknown direct_business concept_only requires_rf_legal_review not_applicable".split(),
    "us_law_dependency": "unknown none low medium high".split(),
    "confidence": "low medium high".split(),
    "source_status": "active archived".split(),
    "notes_status": "indexed reviewed stale".split(),
    "classification_method": "title_heuristic manual_review".split(),
    "metadata_status": "unknown candidate confirmed".split(),
    "legal_signal": "not_detected possible_legal us_specific".split(),
}
TAGS = {"topics": TOPICS, "situations": SITUATIONS, "entity_types": ENTITIES, "business_stage": STAGES}
HEADER = [
    "id", "file", "title", "published_at", "url", "transcript_language",
    "topics", "situations", "entity_types", "business_stage", "concepts",
    "rf_applicability", "us_law_dependency", "confidence", "source_status",
    "manifest_id", "notes_status", "last_reviewed_at", "summary", "indexed_at",
    "source_sha256", "source_bytes", "classification_method", "metadata_status",
    "legal_signal", "legal_evidence",
]
META_HEADER = ["file", "url", "published_at", "status", "evidence", "notes"]
MANIFEST_HEADER = ["file", "bytes", "sha256", "indexed_at"]
US_SIGNAL = re.compile(r"\b(?:small claims court|federal law|JOBS Act|Subchapter V|(?:United States|U\.S\.)\s+(?:law|tax|court)|Internal Revenue Service|IRS|SEC|chapter 11)\b", re.I)
LEGAL_SIGNAL = re.compile(r"\b(?:law|lawsuit|court|statute|legal|attorney|bankruptcy|copyright|trademark|patent|tax|taxes|contract)\b", re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_file(value):
    path = PurePosixPath(value)
    require(bool(value) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and path.as_posix() == value
            and not any(part.startswith(".") for part in path.parts)
            and path.suffix == ".txt", "Invalid source path: " + value)


def read_csv(path, required):
    if not path.exists():
        return []
    require(not path.is_symlink(), "Symlink input: " + str(path))
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None and set(required) <= set(reader.fieldnames)
                and len(reader.fieldnames) == len(set(reader.fieldnames)), "Invalid CSV header: " + str(path))
        rows = list(reader)
    require(all(None not in row and all(v is not None for v in row.values()) for row in rows), "Malformed CSV: " + str(path))
    return rows


def validate_catalog(rows):
    ids, files = set(), set()
    for row in rows:
        ident = row["id"]
        require(bool(re.fullmatch(r"[0-9]{3,}", ident)) and int(ident) > 0
                and int(ident) not in ids, "Invalid/duplicate ID: " + ident)
        ids.add(int(ident))
        safe_file(row["file"])
        require(row["file"] not in files, "Duplicate catalog path")
        files.add(row["file"])
        for field, values in TAGS.items():
            tags = row[field].split(";") if row[field] else []
            require(len(tags) == len(set(tags)) and set(tags) <= set(values), "Invalid tags: " + field)
            if field in ("topics", "situations"):
                require(len(tags) <= 5, "Too many tags")
        for field, values in ENUMS.items():
            if field in row:
                require(row[field] in values, "Invalid enum: " + field)
        if row.get("classification_method") == "title_heuristic":
            require(row["confidence"] == "low", "Heuristic classification must be low confidence")
        if row.get("source_sha256"):
            require(bool(re.fullmatch(r"[a-f0-9]{64}", row["source_sha256"])), "Invalid catalog hash")
        if "source_bytes" in row:
            require(row["source_bytes"].isdigit() and int(row["source_bytes"]) > 0, "Invalid source bytes")
        if row.get("last_reviewed_at"):
            date.fromisoformat(row["last_reviewed_at"])
        if row.get("classification_method") == "manual_review":
            require(bool(row.get("last_reviewed_at")), "Manual review needs review date")


def validate_metadata(rows):
    files = set()
    for row in rows:
        safe_file(row["file"])
        require(row["file"] not in files, "Duplicate metadata path")
        files.add(row["file"])
        require(row["status"] in ENUMS["metadata_status"], "Invalid metadata status")
        if row["url"]:
            url = urlsplit(row["url"])
            require(url.scheme in ("http", "https") and bool(url.hostname)
                    and not url.username and not url.password and not re.search(r"\s", row["url"]), "Invalid source URL")
        if row["published_at"]:
            require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["published_at"])), "Invalid source date")
            date.fromisoformat(row["published_at"])
        if row["status"] == "confirmed":
            require(all(row[k].strip() for k in ("url", "published_at", "evidence")), "Confirmed metadata needs URL, date and match evidence")
        if row["status"] == "unknown":
            require(not any(row[k] for k in ("url", "published_at", "evidence")), "Unknown metadata cannot assert a source match")


def classify(title, text):
    lower = title.lower()
    topics, situations = [], []
    rules = [
        ("payments", r"deadbeat|overdue|bad debts|collect", "client_nonpayment"),
        ("sales", r"\bsell\b|\bselling\b|\bsales\b|pitch|cold calling", ""),
        ("marketing", r"marketing|social media|customers|competition|cold calling|networking|e-commerce", ""),
        ("pricing", r"\bprice\b|pricing", ""),
        ("business_formation", r"starting|startup|start up|business from scratch", "business_startup"),
        ("partnerships", r"partner|management team|advisor", ""),
        ("intellectual_property", r"trademark|copyright|patent|intellectual property", ""),
        ("contracts", r"contract|agreements|negotiating", "contract_negotiation"),
        ("taxes", r"\btax\b|taxes", "tax_issue"),
        ("employment", r"employee|job market", ""),
        ("clients", r"client|deadbeat|overdue", ""),
        ("financing", r"capital|crowdfunding|investor|financ|budget|bankruptcy", ""),
        ("risk_management", r"legal|law|lawsuit|fraud|scam|bankruptcy|risk|franchise", ""),
    ]
    for topic, pattern, situation in rules:
        if re.search(pattern, lower):
            topics.append(topic)
            if situation:
                situations.append(situation)
    if re.search(r"(?:sell|selling) (?:your |a |the )?(?:small )?business\b", lower) and not re.search(r"business (?:plan|pitch)", lower):
        situations.append("business_sale")
    entities = ["small_business"]
    for key, pattern in [("consulting_business", "consult"), ("creative_business", "creative|artist"), ("ecommerce_business", "e-commerce|ebay|amazon"), ("nonprofit", "nonprofit")]:
        if re.search(pattern, lower):
            entities.append(key)
    match = US_SIGNAL.search(text)
    signal = "us_specific" if match else "not_detected"
    if not match:
        match = LEGAL_SIGNAL.search(text)
        if match:
            signal = "possible_legal"
    quote = text[max(0, match.start() - 45):min(len(text), match.end() + 70)] if match else ""
    return {
        "topics": ";".join(topics[:5] or ["operations"]),
        "situations": ";".join(situations[:5]), "entity_types": ";".join(entities),
        "business_stage": "startup" if "business_startup" in situations else "unknown",
        "concepts": "", "rf_applicability": "requires_rf_legal_review" if match else "unknown",
        "us_law_dependency": "high" if signal == "us_specific" else "unknown",
        "confidence": "low", "classification_method": "title_heuristic",
        "legal_signal": signal, "legal_evidence": quote,
        "summary": "Provisional low-confidence title_heuristic tags; literal legal-signal scan of transcript, not semantic review. Title: " + title,
    }


def chunks_for(ident, filename, digest, text):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + 4000, len(text))
        if end < len(text):
            window = text[start + 3000:end]
            boundaries = list(re.finditer(r"[.!?][\"']?\s+", window))
            if not boundaries:
                boundaries = list(re.finditer(r"\s+", window))
            if boundaries:
                end = start + 3000 + boundaries[-1].end()
        chunks.append({"chunk_id": f"{ident}-{len(chunks) + 1:04d}", "catalog_id": ident,
                       "file": filename, "source_sha256": digest,
                       "char_start": start, "char_end": end, "text": text[start:end]})
        start = end
    return chunks


def validate_derived(catalog, manifest, chunks, sources):
    validate_catalog(catalog)
    active = {r["file"]: r for r in catalog if r["source_status"] == "active"}
    require(set(active) == set(sources) == {r["file"] for r in manifest}, "Source/catalog/manifest bijection failed")
    require(len(manifest) == len(sources), "Duplicate manifest rows")
    grouped, ids = {}, set()
    for chunk in chunks:
        require(chunk["chunk_id"] not in ids and chunk["file"] in active, "Invalid/duplicate chunk")
        ids.add(chunk["chunk_id"])
        grouped.setdefault(chunk["file"], []).append(chunk)
    require(set(grouped) == set(sources), "Missing chunk source")
    for item in manifest:
        filename = item["file"]
        payload, text = sources[filename]
        digest = hashlib.sha256(payload).hexdigest()
        require(item["sha256"] == active[filename]["source_sha256"] == digest
                and int(item["bytes"]) == int(active[filename]["source_bytes"]) == len(payload), "Hash/byte mismatch")
        position = 0
        for ordinal, chunk in enumerate(grouped[filename], 1):
            require(chunk["catalog_id"] == active[filename]["id"]
                    and chunk["chunk_id"] == f"{active[filename]['id']}-{ordinal:04d}"
                    and chunk["source_sha256"] == digest and chunk["char_start"] == position
                    and position < chunk["char_end"] <= len(text)
                    and chunk["text"] == text[position:chunk["char_end"]], "Chunk coverage/content mismatch")
            position = chunk["char_end"]
        require(position == len(text), "Incomplete chunk coverage")
        require(not active[filename]["legal_evidence"] or active[filename]["legal_evidence"] in text, "Legal quote not in source")


def csv_text(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def atomic_write(path, content):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def build(root=ROOT):
    root = Path(root).resolve()
    source = root / "Transcriptions"
    require(source.is_dir() and not source.is_symlink(), "Missing/invalid Transcriptions directory")
    sources = {}
    for path in sorted(source.rglob("*.txt")):
        relative = path.relative_to(source).as_posix()
        if any(part.startswith(".") for part in PurePosixPath(relative).parts):
            continue
        safe_file(relative)
        require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents if p != root), "Symlink source")
        payload = path.read_bytes()
        text = payload.decode("utf-8")
        require(bool(text.strip()), "Empty transcript: " + relative)
        sources[relative] = (payload, text)
    require(bool(sources), "No source transcripts")
    old = read_csv(root / "catalog.csv", HEADER[:19])
    validate_catalog(old)
    metadata_path = root / "source-metadata.csv"
    metadata = read_csv(metadata_path, META_HEADER[:-1])
    validate_metadata(metadata)
    metadata_by_file = {r["file"]: r for r in metadata}
    for row in old:
        if row["file"] not in metadata_by_file and (row["url"] or row["published_at"]):
            raise ValueError("Move existing source metadata into source-metadata.csv before rebuilding")
    new_metadata = False
    for filename in sorted(set(sources) | {r["file"] for r in old}):
        if filename not in metadata_by_file:
            row = dict.fromkeys(META_HEADER, "")
            row.update(file=filename, status="unknown")
            metadata.append(row)
            metadata_by_file[filename] = row
            new_metadata = True
    validate_metadata(metadata)
    taxonomy_path = root / "taxonomy.md"
    require(taxonomy_path.is_file() and not taxonomy_path.is_symlink(), "Missing taxonomy")
    taxonomy = taxonomy_path.read_text(encoding="utf-8")
    for key in set(sum(TAGS.values(), []) + sum(ENUMS.values(), [])):
        require("`" + key + "`" in taxonomy, "Missing taxonomy key: " + key)
    manifest_dir = root / "manifests"
    require(manifest_dir.is_dir() and not manifest_dir.is_symlink(), "Missing/invalid manifests directory")
    previous_paths = sorted(p for p in manifest_dir.glob("*.csv") if not p.name.startswith("."))
    previous = read_csv(previous_paths[-1], MANIFEST_HEADER) if previous_paths else []
    previous_by_file = {}
    for row in previous:
        safe_file(row["file"])
        require(row["file"] not in previous_by_file and row["bytes"].isdigit()
                and int(row["bytes"]) > 0 and bool(re.fullmatch(r"[a-f0-9]{64}", row["sha256"])), "Invalid previous manifest")
        previous_by_file[row["file"]] = row
    historical = {}
    for row in old:
        if not row.get("source_sha256"):
            continue
        stamp = row["manifest_id"]
        require(bool(re.fullmatch(r"[0-9]{8}T[0-9]{6}(?:[0-9]{6})?Z", stamp)), "Invalid catalog manifest ID")
        if stamp not in historical:
            history_path = manifest_dir / (stamp + ".csv")
            require(history_path.is_file(), "Missing referenced historical manifest")
            history_rows = read_csv(history_path, MANIFEST_HEADER)
            require(len(history_rows) == len({r["file"] for r in history_rows}), "Duplicate historical manifest path")
            historical[stamp] = {r["file"]: r for r in history_rows}
        item = historical[stamp].get(row["file"])
        require(item is not None and item["sha256"] == row["source_sha256"]
                and item["bytes"] == row["source_bytes"], "Catalog fingerprint differs from referenced manifest")
    now = datetime.now(timezone.utc)
    indexed_at = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest_id = now.strftime("%Y%m%dT%H%M%S%fZ")
    manifest_path = manifest_dir / (manifest_id + ".csv")
    require(not manifest_path.exists(), "Manifest collision")
    old_by_file = {r["file"]: r for r in old}
    next_id = max((int(r["id"]) for r in old), default=0)
    catalog, manifest, chunks = [], [], []
    for filename, (payload, text) in sources.items():
        prior = old_by_file.get(filename)
        if not prior:
            next_id += 1
        ident = prior["id"] if prior else f"{next_id:03d}"
        digest = hashlib.sha256(payload).hexdigest()
        row = dict.fromkeys(HEADER, "")
        row.update(classify(PurePosixPath(filename).stem, text))
        row.update(id=ident, file=filename, title=PurePosixPath(filename).stem,
                   transcript_language="en", source_status="active", manifest_id=manifest_id,
                   notes_status="indexed", indexed_at=indexed_at, source_sha256=digest,
                   source_bytes=str(len(payload)))
        if prior and prior.get("classification_method") == "manual_review":
            row["last_reviewed_at"] = prior["last_reviewed_at"]
            if prior.get("source_sha256") == digest:
                for field in list(TAGS) + ["concepts", "rf_applicability", "us_law_dependency", "confidence", "classification_method", "summary"]:
                    row[field] = prior[field]
                row["notes_status"] = "reviewed"
            else:
                row["notes_status"] = "stale"
        elif prior and prior.get("notes_status") == "stale":
            row["notes_status"] = "stale"
            row["last_reviewed_at"] = prior.get("last_reviewed_at", "")
        meta = metadata_by_file[filename]
        row["metadata_status"] = meta["status"]
        if meta["status"] == "confirmed":
            row.update(url=meta["url"], published_at=meta["published_at"])
        catalog.append(row)
        manifest.append(dict(file=filename, bytes=str(len(payload)), sha256=digest, indexed_at=indexed_at))
        chunks.extend(chunks_for(ident, filename, digest, text))
    for filename, prior in old_by_file.items():
        if filename not in sources:
            row = {k: prior.get(k, "") for k in HEADER}
            row["source_status"] = "archived"
            if not row["classification_method"]:
                row.update(classify(row["title"], ""))
                row.update(last_reviewed_at="", notes_status="indexed")
            meta = metadata_by_file[filename]
            row.update(metadata_status=meta["status"], url=meta["url"] if meta["status"] == "confirmed" else "",
                       published_at=meta["published_at"] if meta["status"] == "confirmed" else "")
            if not row["source_sha256"] and filename in previous_by_file:
                row.update(source_sha256=previous_by_file[filename]["sha256"], source_bytes=previous_by_file[filename]["bytes"])
            require(bool(row["source_sha256"]), "Archived source needs a prior fingerprint")
            catalog.append(row)
    catalog.sort(key=lambda r: int(r["id"]))
    validate_derived(catalog, manifest, chunks, sources)
    current = {r["file"]: r for r in manifest}
    changes = {
        "added": sorted(set(current) - set(previous_by_file)),
        "removed": sorted(set(previous_by_file) - set(current)),
        "changed": sorted(f for f in set(current) & set(previous_by_file)
                          if (current[f]["sha256"], current[f]["bytes"]) != (previous_by_file[f]["sha256"], previous_by_file[f]["bytes"])),
    }
    metadata_counts = {status: sum(r["metadata_status"] == status for r in catalog)
                       for status in ENUMS["metadata_status"]}
    source_review = "externally_supplied_metadata" if metadata_counts["confirmed"] or metadata_counts["candidate"] else "not_run"
    report = "\n".join([
        "# Index Validation", "", "structural_status: verified", "semantic_review: not_run",
        f"source_match_review: {source_review}", "generator_source_verification: not_run",
        "ai_learning_checks: not_run", "independent_validation: pending", "",
        "Checks executed before output replacement: UTF-8/nonempty sources; unique paths and IDs; canonical tags/enums;",
        "source/catalog/manifest bijection; exact SHA256 and byte sizes; complete nonoverlapping chunk coverage; exact legal quotes; metadata shape/evidence requirements.",
        "", f"Manifest: {manifest_id}", f"Previous manifest: {previous_paths[-1].name if previous_paths else 'none (baseline)'}",
        f"Active records: {len(sources)}", f"Archived records: {len(catalog) - len(sources)}", f"Chunks: {len(chunks)}",
        f"Stale review records: {sum(r['notes_status'] == 'stale' for r in catalog)}",
        f"Confirmed metadata records: {metadata_counts['confirmed']}",
        f"Candidate metadata records: {metadata_counts['candidate']}",
        f"Unknown metadata records: {metadata_counts['unknown']}",
        "", "Change detection (no previous manifest means initial baseline):", json.dumps(changes, ensure_ascii=True, sort_keys=True), "",
        "Title tags are provisional, low confidence unless explicitly manually reviewed. Legal keyword signals are not legal conclusions.",
        "Source matching uses externally supplied metadata, not independently verified by the generator. Counts describe supplied statuses, not proof of source truth.",
        "Candidate URLs/dates remain authoritative-table candidates; only confirmed values enter the catalog. published_at is video publication/upload date, not recording date.",
        "No semantic review of all transcripts, ASR correction, full transcript fidelity check or external AI tests is claimed.",
        "Outputs are atomically replaced per file, NOT as a multi-file transaction. On interruption rerun and compare manifest/report IDs.", "",
    ])
    outputs = [(manifest_path, csv_text(MANIFEST_HEADER, manifest)),
               (root / "catalog.csv", csv_text(HEADER, catalog)),
               (root / "chunks.jsonl", "".join(json.dumps(c, ensure_ascii=True) + "\n" for c in chunks)),
               (root / "review-report.md", report)]
    if new_metadata:
        # Existing authoritative rows (including optional columns) are preserved.
        meta_header = list(dict.fromkeys(META_HEADER + [k for r in metadata for k in r]))
        outputs.insert(0, (metadata_path, csv_text(meta_header, metadata)))
    for path, _ in outputs:
        require(not path.is_symlink() and (not path.exists() or path.is_file()), "Invalid output destination: " + str(path))
    # Recheck the input bytes and inventory immediately before writing derived files.
    live_paths = {p.relative_to(source).as_posix() for p in source.rglob("*.txt")
                  if not any(part.startswith(".") for part in p.relative_to(source).parts)}
    require(live_paths == set(sources) and all((source / f).read_bytes() == value[0] for f, value in sources.items()), "Sources changed during build")
    for path, content in outputs:
        atomic_write(path, content)
    result = {"active": len(sources), "archived": len(catalog) - len(sources),
              "chunks": len(chunks), "manifest": str(manifest_path), "changes": changes,
              "structural_status": "verified", "semantic_review": "not_run", "ai_learning_checks": "not_run",
              "metadata_counts": metadata_counts, "source_match_review": source_review}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return result


if __name__ == "__main__":
    try:
        build()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit("Build failed before completion: " + str(error)) from error
