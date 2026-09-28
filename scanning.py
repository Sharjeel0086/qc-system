"""Turns a scanned barcode / QR payload into unit field values.

Almost every industrial USB scanner behaves as a keyboard: it types the code
into whatever box has focus and then sends Enter. So no driver or library is
needed - the work is in *interpreting* what was typed, because a single QR
code on an LED unit usually carries several pieces of information at once.

This module is pure logic with no Tkinter in it, so it can be tested on its
own.

Parse types
-----------
raw        the whole payload is one field
delimited  key/value pairs, e.g.  SN:ABC123;MODEL:43UHD;PANEL:P9
split      positional parts,  e.g. ABC123,43UHD,P9
regex      a pattern with named groups
json       the QR holds a JSON object
fixed      fixed character positions, e.g. chars 0-10 are the serial
"""

import json
import re


class ScanParseError(Exception):
    """The payload did not match the rule configured for this scan step."""


PARSE_TYPES = ("raw", "delimited", "split", "regex", "json", "fixed")

PARSE_TYPE_HELP = {
    "raw": "The whole scanned code goes into one field. Use this for a plain "
           "serial barcode or a main board QR that holds only the board "
           "number.",
    "delimited": "The code holds key/value pairs, like  SN:ABC123;MODEL:43UHD"
                 "  - map each key to a field.",
    "split": "The code is one line split by a separator, like  ABC123,43UHD,P9"
             "  - map each position (0, 1, 2 ...) to a field.",
    "regex": "Use a regular expression with named groups. Each group name "
             "must match a field id.",
    "json": "The QR code holds a JSON object like  {\"sn\":\"ABC\","
            "\"model\":\"43UHD\"}  - map each key to a field.",
    "fixed": "The code is fixed width. Give each field a start and end "
             "character position.",
}


def _apply_transforms(text, cfg):
    if cfg.get("trim", True):
        text = text.strip()
    if cfg.get("upper"):
        text = text.upper()
    if cfg.get("strip_prefix"):
        prefix = cfg["strip_prefix"]
        if text.startswith(prefix):
            text = text[len(prefix):]
    if cfg.get("strip_suffix"):
        suffix = cfg["strip_suffix"]
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text


def _clean_values(values, cfg):
    out = {}
    for key, val in values.items():
        if val is None:
            continue
        val = str(val).strip()
        if cfg.get("upper"):
            val = val.upper()
        if val:
            out[key] = val
    return out


def parse_scan(payload, rule):
    """Return {field_id: value} for one scanned payload.

    `rule` is the dict stored in checksheets.json for this scan step.
    Raises ScanParseError with a message an operator can act on.
    """
    if payload is None or not str(payload).strip():
        raise ScanParseError("Nothing was scanned.")

    rule = rule or {}
    ptype = rule.get("type", "raw")
    text = _apply_transforms(str(payload), rule)

    if not text:
        raise ScanParseError("The scanned code was empty after trimming.")

    if ptype == "raw":
        return _parse_raw(text, rule)
    if ptype == "delimited":
        return _parse_delimited(text, rule)
    if ptype == "split":
        return _parse_split(text, rule)
    if ptype == "regex":
        return _parse_regex(text, rule)
    if ptype == "json":
        return _parse_json(text, rule)
    if ptype == "fixed":
        return _parse_fixed(text, rule)

    raise ScanParseError(f"Unknown parse type '{ptype}'.")


def _parse_raw(text, rule):
    target = rule.get("target")
    if not target:
        raise ScanParseError("This scan step has no target field set.")
    if rule.get("regex"):
        match = re.search(rule["regex"], text)
        if not match:
            raise ScanParseError(
                "The scanned code did not match the expected pattern.")
        text = match.group(1) if match.groups() else match.group(0)
    return _clean_values({target: text}, rule)


def _parse_delimited(text, rule):
    sep = rule.get("separator", ";")
    pair_sep = rule.get("pair_separator", ":")
    mapping = {str(k).strip().upper(): v
               for k, v in (rule.get("map") or {}).items()}
    if not mapping:
        raise ScanParseError("This scan step has no key mapping set.")

    found = {}
    unknown = []
    for chunk in text.split(sep):
        chunk = chunk.strip()
        if not chunk or pair_sep not in chunk:
            continue
        key, _, value = chunk.partition(pair_sep)
        key = key.strip().upper()
        if key in mapping:
            found[mapping[key]] = value
        else:
            unknown.append(key)

    if not found:
        keys = ", ".join(sorted(mapping))
        raise ScanParseError(
            f"No expected keys found in the scanned code. Looking for: {keys}."
            + (f" Found instead: {', '.join(unknown[:6])}." if unknown else ""))
    return _clean_values(found, rule)


def _parse_split(text, rule):
    sep = rule.get("separator", ",")
    mapping = rule.get("map") or {}
    if not mapping:
        raise ScanParseError("This scan step has no position mapping set.")

    parts = [p.strip() for p in text.split(sep)]
    found = {}
    for pos, field in mapping.items():
        try:
            index = int(pos)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(parts):
            found[field] = parts[index]

    if not found:
        raise ScanParseError(
            f"The scanned code split into {len(parts)} part(s), which does not "
            "match the positions configured for this step.")
    return _clean_values(found, rule)


def _parse_regex(text, rule):
    pattern = rule.get("pattern")
    if not pattern:
        raise ScanParseError("This scan step has no pattern set.")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ScanParseError(f"The pattern is not valid: {exc}") from exc
    if not compiled.groupindex:
        raise ScanParseError(
            "The pattern has no named groups. Use (?P<serial_number>...) so "
            "each group knows which field it fills.")
    match = compiled.search(text)
    if not match:
        raise ScanParseError(
            "The scanned code did not match the expected pattern.")
    return _clean_values(match.groupdict(), rule)


def _parse_json(text, rule):
    mapping = rule.get("map") or {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScanParseError(
            f"The scanned code is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ScanParseError("The scanned JSON is not an object.")

    found = {}
    if mapping:
        lower = {str(k).lower(): v for k, v in data.items()}
        for key, field in mapping.items():
            if str(key).lower() in lower:
                found[field] = lower[str(key).lower()]
    else:
        found = dict(data)

    if not found:
        raise ScanParseError(
            "None of the mapped keys were present in the scanned JSON.")
    return _clean_values(found, rule)


def _parse_fixed(text, rule):
    slices = rule.get("slices") or {}
    if not slices:
        raise ScanParseError("This scan step has no character positions set.")
    found = {}
    for field, bounds in slices.items():
        try:
            start, end = int(bounds[0]), int(bounds[1])
        except (TypeError, ValueError, IndexError):
            continue
        piece = text[start:end]
        if piece:
            found[field] = piece
    if not found:
        raise ScanParseError(
            f"The scanned code is only {len(text)} character(s) long, shorter "
            "than the positions configured for this step.")
    return _clean_values(found, rule)


# --- helpers used by the builder screen ---------------------------------

def mapping_to_text(mapping):
    """{'SN': 'serial_number'} -> 'SN = serial_number' lines."""
    return "\n".join(f"{k} = {v}" for k, v in (mapping or {}).items())


def text_to_mapping(text):
    """'SN = serial_number' lines -> {'SN': 'serial_number'}."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if key and value:
            out[key] = value
    return out


def slices_to_text(slices):
    """{'serial_number': [0, 10]} -> 'serial_number = 0, 10' lines."""
    return "\n".join(f"{k} = {v[0]}, {v[1]}"
                     for k, v in (slices or {}).items() if len(v) >= 2)


def text_to_slices(text):
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        field, sep, bounds = line.partition("=")
        if not sep:
            continue
        parts = [p.strip() for p in bounds.split(",")]
        if len(parts) < 2:
            continue
        try:
            out[field.strip()] = [int(parts[0]), int(parts[1])]
        except ValueError:
            continue
    return out


def describe_rule(rule):
    """One-line human summary of a scan rule, for list views."""
    rule = rule or {}
    ptype = rule.get("type", "raw")
    if ptype == "raw":
        return f"whole code into '{rule.get('target', '?')}'"
    if ptype == "delimited":
        return (f"key/value split by '{rule.get('separator', ';')}' -> "
                f"{len(rule.get('map') or {})} field(s)")
    if ptype == "split":
        return (f"positions split by '{rule.get('separator', ',')}' -> "
                f"{len(rule.get('map') or {})} field(s)")
    if ptype == "regex":
        return "pattern with named groups"
    if ptype == "json":
        return f"JSON object -> {len(rule.get('map') or {})} field(s)"
    if ptype == "fixed":
        return f"fixed positions -> {len(rule.get('slices') or {})} field(s)"
    return ptype
