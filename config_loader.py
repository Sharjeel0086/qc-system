"""Reads, validates and writes data/checksheets.json.

The builder screen edits these objects and calls save_checksheets(), so this
module is the only place that touches the file.
"""

import json
import os
import re
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "checksheets.json")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")

MANDATORY_FIELDS = ("serial_number", "main_board_no")
FIELD_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
SHEET_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$")


class ConfigError(Exception):
    pass


class UnitField:
    def __init__(self, data):
        self.id = data["id"]
        self.label = data.get("label") or self.id.replace("_", " ").capitalize()
        self.required = bool(data.get("required", False))
        if self.id in MANDATORY_FIELDS:
            self.required = True

    def to_dict(self):
        return {"id": self.id, "label": self.label, "required": self.required}


class ScanTarget:
    """One scan step: a code the operator scans, and how to read it."""

    def __init__(self, data):
        self.id = data.get("id") or "scan"
        self.label = data.get("label") or "Scan code"
        self.prompt = data.get("prompt") or f"Scan the {self.label.lower()}"
        self.rule = data.get("rule") or {"type": "raw"}

    @property
    def target_fields(self):
        """Which unit fields this step can fill."""
        rule = self.rule
        ptype = rule.get("type", "raw")
        if ptype == "raw":
            return [rule["target"]] if rule.get("target") else []
        if ptype in ("delimited", "split", "json"):
            return list((rule.get("map") or {}).values())
        if ptype == "fixed":
            return list((rule.get("slices") or {}).keys())
        if ptype == "regex":
            try:
                return list(re.compile(rule.get("pattern", "")).groupindex)
            except re.error:
                return []
        return []

    def to_dict(self):
        return {"id": self.id, "label": self.label, "prompt": self.prompt,
                "rule": self.rule}


class Checksheet:
    def __init__(self, key, data):
        self.key = key
        self.name = data.get("name") or key
        self.subtitle = data.get("subtitle", "")
        self.tests = [str(t).strip() for t in data.get("tests", [])
                      if str(t).strip()]
        self.unit_fields = [UnitField(f) for f in data.get("unit_fields", [])
                            if f.get("id")]
        self.scan_targets = [ScanTarget(s)
                             for s in data.get("scan_targets", [])]

        present = {f.id for f in self.unit_fields}
        for missing in MANDATORY_FIELDS:
            if missing not in present:
                label = ("Serial number" if missing == "serial_number"
                         else "Main board number")
                self.unit_fields.insert(
                    0, UnitField({"id": missing, "label": label,
                                  "required": True}))

    @property
    def test_count(self):
        return len(self.tests)

    @property
    def field_ids(self):
        return [f.id for f in self.unit_fields]

    def field_label(self, field_id):
        for f in self.unit_fields:
            if f.id == field_id:
                return f.label
        return field_id

    def scannable_fields(self):
        """Field ids that at least one scan step can fill."""
        out = set()
        for target in self.scan_targets:
            out.update(target.target_fields)
        return out

    def to_dict(self):
        return {
            "name": self.name,
            "subtitle": self.subtitle,
            "unit_fields": [f.to_dict() for f in self.unit_fields],
            "scan_targets": [s.to_dict() for s in self.scan_targets],
            "tests": list(self.tests),
        }

    def clone(self, new_key):
        data = self.to_dict()
        data["name"] = self.name + " (copy)"
        return Checksheet(new_key, data)


# --- load / save ---------------------------------------------------------

def load_checksheets(path=CONFIG_PATH):
    if not os.path.exists(path):
        raise ConfigError(f"Configuration file not found:\n{path}")

    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"checksheets.json has a syntax error on line {exc.lineno}: "
                f"{exc.msg}") from exc

    sheets = {}
    for key, data in raw.items():
        if key.startswith("_") or not isinstance(data, dict):
            continue
        sheet = Checksheet(key, data)
        if sheet.tests:
            sheets[key] = sheet

    if not sheets:
        raise ConfigError(
            "No usable check sheets found. Every sheet needs at least one "
            "test.")
    return sheets


def save_checksheets(sheets, path=CONFIG_PATH):
    """Write sheets (dict of key -> Checksheet) to disk, keeping a backup."""
    if not sheets:
        raise ConfigError("There must be at least one check sheet.")

    payload = {"_comment": "You do not need to edit this file by hand. Use "
                           "Tools > Check sheet builder inside the program."}
    for key, sheet in sheets.items():
        payload[key] = sheet.to_dict()

    if os.path.exists(path):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, os.path.join(BACKUP_DIR,
                                        f"checksheets_{stamp}.json"))
        _trim_backups()

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _trim_backups(keep=20):
    try:
        files = sorted(os.listdir(BACKUP_DIR))
        for name in files[:-keep]:
            os.remove(os.path.join(BACKUP_DIR, name))
    except OSError:
        pass


# --- validation used by the builder -------------------------------------

def validate_sheet(key, sheet, all_keys=()):
    """Return a list of problem strings; empty means the sheet is fine."""
    problems = []

    if not SHEET_KEY_RE.match(key):
        problems.append(
            f"The code '{key}' must be 1-16 letters, digits, '-' or '_', "
            "starting with a letter or digit.")
    if list(all_keys).count(key) > 1:
        problems.append(f"The code '{key}' is used more than once.")
    if not sheet.name.strip():
        problems.append("The check sheet needs a name.")
    if not sheet.tests:
        problems.append("Add at least one test.")

    seen = []
    for field in sheet.unit_fields:
        if not FIELD_ID_RE.match(field.id):
            problems.append(
                f"Field id '{field.id}' must be lowercase letters, digits and "
                "underscores, starting with a letter.")
        if field.id in seen:
            problems.append(f"Field id '{field.id}' appears twice.")
        seen.append(field.id)
        if not field.label.strip():
            problems.append(f"Field '{field.id}' needs a label.")

    for missing in MANDATORY_FIELDS:
        if missing not in seen:
            problems.append(
                f"The field '{missing}' is required on every check sheet.")

    for target in sheet.scan_targets:
        if not target.label.strip():
            problems.append("A scan step has no label.")
        fields = target.target_fields
        if not fields:
            problems.append(
                f"Scan step '{target.label}' does not fill any field yet.")
        for field_id in fields:
            if field_id not in seen:
                problems.append(
                    f"Scan step '{target.label}' fills '{field_id}', which is "
                    "not a field on this sheet.")

    for dupe in sorted({t for t in sheet.tests if sheet.tests.count(t) > 1}):
        problems.append(f"The test '{dupe}' is listed more than once.")

    return problems


def suggest_field_id(label):
    """'Main board number' -> 'main_board_no'-ish slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    if not slug or not slug[0].isalpha():
        slug = "field_" + slug
    return slug[:40]
