"""Camera capture, barcode decoding, and OCR-verified serial number scanning.

Three things live here, for whenever a physical scanner isn't at the station:

* PhotoCaptureDialog   - take a test photo with a webcam instead of picking
  a file.
* ScanCaptureDialog    - read a QR code or a 1D barcode by pointing a
  webcam at it, instead of using a handheld scanner. Barcode only.
* VerifiedScanDialog   - for labels where the printed serial number sits
  above its own barcode (e.g. the Haier unit labels this project scans):
  reads BOTH the printed text (via OCR) and the barcode, cross-checks them
  against each other, and only accepts a result once the same value has
  shown up on several consecutive camera frames. Built because barcode
  decoding alone isn't always reliable enough for a QC record on its own.

BARCODE READING uses two independent decoders, tried in this order:

  1. pyzbar, if it's installed. This is the one that matters most for
     alphanumeric serial-number labels (things like "DH20RQ002013C90J0501"):
     those are almost always Code 39, and OpenCV's own barcode reader
     CANNOT read Code 39 at all - not a quality issue, it was simply never
     built to decode that symbology (confirmed against a real Code 39-style
     label: OpenCV located the barcode's bounding box correctly but always
     returned empty content, at every resolution tried). pyzbar (via the
     zbar library) reads Code 39, Code 93, Codabar, Code 128, EAN, UPC and
     QR - effectively everything.
  2. A built-in Code 39 decoder that reads the standard nine-element
     wide/narrow pattern directly from the camera pixels. It does not need
     ZBar, a system DLL, or administrator rights.
  3. OpenCV's own barcode and QR detectors (from opencv-contrib-python), as
     a fallback for EAN/UPC, Code-128 and QR.

OCR READING (VerifiedScanDialog only) uses Tesseract via pytesseract:

  1. OpenCV's barcode detector locates the barcode's bounding box (it can
     do this reliably even though it can't decode Code 39 - detecting the
     shape and decoding its content are different steps).
  2. The frame is deskewed using the barcode's own tilt angle - the printed
     text above it is part of the same rigid label, so it shares the tilt.
  3. The band of the image directly above the barcode is cropped out (that
     band is where the printed serial number lives on this label layout).
  4. Tesseract reads that band, and the longest run of A-Z0-9 characters it
     finds is taken as the candidate serial number.

Needs opencv-contrib-python (NOT plain opencv-python - see
requirements.txt for why), Pillow to show the live picture, and for OCR
specifically, pytesseract plus the separate Tesseract-OCR program (pip only
installs the Python wrapper, not the underlying engine - see
requirements.txt and the README for the Windows installer link). Install
the pip packages with:

    pip install -r requirements.txt

or run "Install Camera Requirements.bat". Everything here fails soft: if a
package is missing, or no camera is found, the app shows a plain message
instead of crashing - file upload, a physical scanner, and typing details
by hand all keep working regardless of what's installed.

A note on image quality separate from symbology: 1D barcodes need their
narrowest bar to be at least a few pixels wide in the captured frame to
decode reliably at all, with either library. A blurry, distant, or heavily
compressed shot of a long alphanumeric code can fail even when everything
above is installed correctly - fill more of the frame with the label and
hold the camera steady if scans are inconsistent.
"""

import math
import os
import re
import tempfile
import tkinter as tk
from tkinter import messagebox

import theme

try:
    import cv2
    HAVE_CV2 = True
except ImportError as exc:
    HAVE_CV2 = False
    _CV2_ERROR = str(exc)

HAVE_CV2_BARCODE = False
if HAVE_CV2:
    HAVE_CV2_BARCODE = hasattr(cv2, "barcode_BarcodeDetector")

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

try:
    from PIL import Image, ImageTk
    HAVE_PIL = True
except ImportError as exc:
    HAVE_PIL = False
    _PIL_ERROR = str(exc)

try:
    from pyzbar import pyzbar
    HAVE_PYZBAR = True
except ImportError as exc:
    HAVE_PYZBAR = False
    _PYZBAR_ERROR = str(exc)
except OSError as exc:
    # The common Windows failure: pip install succeeded but the bundled
    # zbar DLL didn't load (usually a missing Visual C++ Redistributable).
    HAVE_PYZBAR = False
    _PYZBAR_ERROR = str(exc)

try:
    import pytesseract
    HAVE_PYTESSERACT = True
except ImportError as exc:
    HAVE_PYTESSERACT = False
    _PYTESSERACT_ERROR = str(exc)

# pip installs the pytesseract wrapper, never the Tesseract program itself -
# that's a separate Windows installer (see requirements.txt). If it's not
# on PATH, try the two locations the official Windows installer defaults to
# before giving up.
HAVE_TESSERACT_BINARY = False
_TESSERACT_ERROR = ""
if HAVE_PYTESSERACT:
    _WINDOWS_TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    try:
        pytesseract.get_tesseract_version()
        HAVE_TESSERACT_BINARY = True
    except Exception as exc:
        _TESSERACT_ERROR = str(exc)
        for _path in _WINDOWS_TESSERACT_PATHS:
            if os.path.isfile(_path):
                pytesseract.pytesseract.tesseract_cmd = _path
                try:
                    pytesseract.get_tesseract_version()
                    HAVE_TESSERACT_BINARY = True
                    _TESSERACT_ERROR = ""
                    break
                except Exception as exc2:
                    _TESSERACT_ERROR = str(exc2)

# Code 39 is a simple 9-element wide/narrow symbology.  We keep a small
# built-in decoder here so the QC station does NOT depend on ZBar, a native
# Windows DLL, or administrator-installed software.  This is particularly
# useful on locked-down company PCs.  The table is the standard Code 39
# character set: 43 data characters plus the * start/stop character.
_CODE39_WIDTH_PATTERNS = {
    "0":"NNNWWNWNN", "1":"WNNWNNNNW", "2":"NNWWNNNNW", "3":"WNWWNNNNN",
    "4":"NNNWWNNNW", "5":"WNNWWNNNN", "6":"NNWWWNNNN", "7":"NNNWNNWNW",
    "8":"WNNWNNWNN", "9":"NNWWNNWNN", "A":"WNNNNWNNW", "B":"NNWNNWNNW",
    "C":"WNWNNWNNN", "D":"NNNNWWNNW", "E":"WNNNWWNNN", "F":"NNWNWWNNN",
    "G":"NNNNNWWNW", "H":"WNNNNWWNN", "I":"NNWNNWWNN", "J":"NNNNWWWNN",
    "K":"WNNNNNNWW", "L":"NNWNNNNWW", "M":"WNWNNNNWN", "N":"NNNNWNNWW",
    "O":"WNNNWNNWN", "P":"NNWNWNNWN", "Q":"NNNNNNWWW", "R":"WNNNNNWWN",
    "S":"NNWNNNWWN", "T":"NNNNWNWWN", "U":"WWNNNNNNW", "V":"NWWNNNNNW",
    "W":"WWWNNNNNN", "X":"NWNNWNNNW", "Y":"WWNNWNNNN", "Z":"NWWNWNNNN",
    "-":"NWNNNNWNW", ".":"WWNNNNWNN", " ":"NWWNNNWNN", "$":"NWNWNWNNN",
    "/":"NWNWNNNWN", "+":"NWNNNWNWN", "%":"NNNWNWNWN", "*":"NWNNWNWNN",
}
_CODE39_PATTERN_TO_CHAR = {v: k for k, v in _CODE39_WIDTH_PATTERNS.items()}
CAN_READ_MANUAL_CODE39 = HAVE_CV2 and HAVE_NUMPY

CAMERA_READY = HAVE_CV2 and HAVE_PIL
CAN_READ_CODE128_FAMILY = HAVE_CV2_BARCODE or HAVE_PYZBAR
CAN_READ_CODE39_FAMILY = HAVE_PYZBAR or CAN_READ_MANUAL_CODE39
CAN_READ_BARCODES = CAN_READ_CODE128_FAMILY or CAN_READ_MANUAL_CODE39  # backward compatible
CAN_READ_SERIAL_TEXT = HAVE_PYTESSERACT and HAVE_TESSERACT_BINARY and HAVE_NUMPY

SERIAL_LENGTH = 20
SERIAL_RE = re.compile(r"[A-Z0-9]{%d}" % SERIAL_LENGTH)

INSTALL_MESSAGE = (
    "Camera features need a couple of extra packages that are not "
    "installed yet.\n\n"
    "Run \"Install Camera Requirements.bat\" in the program folder, or "
    "open a command prompt there and run:\n\n"
    "    pip install -r requirements.txt\n\n"
    "Then restart the program. Everything else works normally without it -"
    " use file upload for photos and a handheld scanner (or type the "
    "details by hand) for codes."
)

BARCODE_LIMITED_MESSAGE = (
    "ZBar/pyzbar is not available, but this build has its own built-in "
    "Code 39 decoder. Camera scanning can therefore continue without "
    "administrator rights or a Windows DLL installation."
)

OCR_NOT_SET_UP_MESSAGE = (
    "OCR needs Tesseract, which isn't found yet.\n\n"
    "pip only installs the Python wrapper (pytesseract) - Tesseract itself "
    "is a separate free program. Download and run the Windows installer "
    "from:\n\n"
    "    https://github.com/UB-Mannheim/tesseract/wiki\n\n"
    "Use the default install location, then restart this program. Barcode "
    "scanning keeps working normally without OCR."
)


def require_camera(parent=None):
    """Show a message and return False if the camera cannot be used."""
    if not CAMERA_READY:
        messagebox.showinfo("Camera not set up", INSTALL_MESSAGE, parent=parent)
        return False
    return True


def diagnostics_text():
    """Human-readable status of every camera dependency, for troubleshooting."""
    lines = []
    lines.append(f"OpenCV (camera + code reading): "
                 f"{'available' if HAVE_CV2 else 'NOT available'}")
    if not HAVE_CV2:
        lines.append(f"    import error: {_CV2_ERROR}")
    lines.append(f"OpenCV barcode reader - EAN/UPC/Code-128 only, NEVER "
                 f"Code 39 (needs opencv-contrib-python): "
                 f"{'available' if HAVE_CV2_BARCODE else 'NOT available'}")
    lines.append(f"Pillow (shows the live picture): "
                 f"{'available' if HAVE_PIL else 'NOT available'}")
    if not HAVE_PIL:
        lines.append(f"    import error: {_PIL_ERROR}")
    lines.append(f"pyzbar/ZBar - optional native decoder: "
                 f"{'available' if HAVE_PYZBAR else 'NOT available'}")
    if not HAVE_PYZBAR:
        lines.append(f"    optional decoder error: {_PYZBAR_ERROR}")
    lines.append(f"Built-in Code 39 decoder (no ZBar/DLL required): "
                 f"{'available' if CAN_READ_MANUAL_CODE39 else 'NOT available'}")
    lines.append(f"pytesseract (OCR wrapper): "
                 f"{'available' if HAVE_PYTESSERACT else 'NOT available'}")
    if not HAVE_PYTESSERACT:
        lines.append(f"    import error: {_PYTESSERACT_ERROR}")
    lines.append(f"Tesseract-OCR program (the actual OCR engine, installed "
                 f"separately from pip - see README): "
                 f"{'available' if HAVE_TESSERACT_BINARY else 'NOT available'}")
    if HAVE_PYTESSERACT and not HAVE_TESSERACT_BINARY:
        lines.append(f"    error: {_TESSERACT_ERROR}")
    lines.append("")
    if CAMERA_READY and CAN_READ_CODE39_FAMILY:
        lines.append("Camera photo capture: ready.")
        lines.append("Camera barcode scanning: ready for QR, Code 39, Code "
                     "128, EAN/UPC and Codabar. Code 39 does not require "
                     "pyzbar/ZBar in this build.")
    elif CAMERA_READY and CAN_READ_CODE128_FAMILY:
        lines.append("Camera photo capture: ready.")
        lines.append("Camera barcode scanning: QR/Code-128/EAN/UPC available. "
                     "Built-in Code 39 decoder is unavailable because the "
                     "camera/numeric dependencies are missing.")
    elif CAMERA_READY:
        lines.append("Camera photo capture: ready.")
        lines.append("Camera barcode scanning: QR codes only - both "
                     "barcode readers (opencv-contrib-python and pyzbar) "
                     "are missing or failed to load, see above.")
    else:
        lines.append("Camera features are not usable yet - see above for "
                     "what's missing.")
    lines.append("Camera OCR (printed serial number reading): "
                 f"{'ready' if CAN_READ_SERIAL_TEXT else 'NOT ready'}")
    return "\n".join(lines)


def print_diagnostics():
    """Called from the command line by the installer .bat to show status."""
    print(diagnostics_text())


def _barcode_variants(frame):
    """Yield practical image variants for ZBar/OpenCV.

    Webcam exposure, glare and small 1-D bars are the common reasons a
    decoder misses an otherwise valid barcode.  We keep the original frame
    first, then try grayscale/contrast/threshold variants.  A modest upscale
    is also tried because long Code-39 labels can otherwise have very narrow
    bars at the camera resolution.
    """
    if frame is None:
        return
    yield frame
    if not HAVE_CV2 or not HAVE_NUMPY:
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    yield gray

    # Contrast normalization helps under uneven factory lighting.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    yield enhanced

    # Two binary variants; keep both because either black/white polarity may
    # be more readable depending on the label and lighting.
    _, otsu = cv2.threshold(enhanced, 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield otsu
    yield cv2.bitwise_not(otsu)

    # Upscale only after the cheaper full-resolution attempts.
    up = cv2.resize(gray, None, fx=1.7, fy=1.7,
                    interpolation=cv2.INTER_CUBIC)
    yield up



def _code39_decode_scanline(row):
    """Decode one horizontal black/white scan line as Code 39.

    Code 39 uses nine alternating bar/space elements per character, with
    exactly three wide elements. Characters are separated by one narrow
    white gap and the symbol is delimited by '*' start/stop characters.
    The decoder estimates wide/narrow from each character rather than
    assuming one fixed pixel width, so camera distance can change freely.
    """
    if row is None or not HAVE_NUMPY:
        return ""
    arr = np.asarray(row)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    # A small hysteresis-free threshold is intentional: callers supply
    # grayscale/binary variants separately, and this keeps the run parser
    # deterministic.
    dark = (arr < 128).astype(np.uint8)
    black = np.flatnonzero(dark)
    if black.size < 20:
        return ""
    dark = dark[black[0]:black[-1] + 1]
    changes = np.flatnonzero(dark[1:] != dark[:-1]) + 1
    vals = dark[np.r_[0, changes]]
    widths = np.diff(np.r_[0, changes, len(dark)]).astype(float)
    if vals.size and vals[0] == 0:
        vals = vals[1:]
        widths = widths[1:]
    n = len(widths)
    if n < 9:
        return ""
    colour_pattern = [1, 0, 1, 0, 1, 0, 1, 0, 1]

    for start in range(0, n - 8):
        if vals[start:start + 9].tolist() != colour_pattern:
            continue
        out = []
        pos = start
        while pos + 9 <= n:
            if vals[pos:pos + 9].tolist() != colour_pattern:
                break
            ew = widths[pos:pos + 9]
            order = np.argsort(ew)
            wide_idx = set(int(i) for i in order[-3:])
            wide = float(min(ew[list(wide_idx)]))
            narrow_values = [float(ew[i]) for i in range(9) if i not in wide_idx]
            narrow = max(narrow_values)
            # Require an actual wide/narrow separation.  The relaxed upper
            # bound allows ordinary camera blur and perspective distortion.
            if narrow <= 0 or wide < 1.25 * narrow:
                break
            pattern = ''.join('W' if i in wide_idx else 'N' for i in range(9))
            ch = _CODE39_PATTERN_TO_CHAR.get(pattern)
            if ch is None:
                break
            out.append(ch)
            pos += 9

            # Stop character has no following inter-character gap requirement
            # for decoding purposes; it is the final nine-element symbol.
            if ch == '*' and len(out) > 1:
                if len(out) >= 3 and out[-1] == '*':
                    return ''.join(out[1:-1])
                break

            if pos >= n or vals[pos] != 0:
                break
            gap = float(widths[pos])
            if gap < 0.35 * narrow or gap > 2.0 * narrow:
                break
            pos += 1
    return ""


def _code39_decode_image(gray):
    """Try many horizontal scan lines in a grayscale/binary image."""
    if gray is None or not HAVE_CV2 or not HAVE_NUMPY:
        return ""
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if h < 10 or w < 50:
        return ""

    variants = [gray]
    # Local contrast and binary variants improve performance under factory
    # lighting and on slightly faded thermal labels.
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        variants.append(clahe.apply(gray))
        _, otsu = cv2.threshold(clahe.apply(gray), 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.extend([otsu, cv2.bitwise_not(otsu)])
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 7)
        variants.extend([adaptive, cv2.bitwise_not(adaptive)])
    except cv2.error:
        pass

    # Sample the middle of the frame densely first; a 1-D barcode has many
    # identical horizontal slices, so one good slice is sufficient.
    y_positions = sorted(set(
        [int(y) for y in np.linspace(0.12 * h, 0.88 * h, min(41, max(9, h // 8)))]
        + [int(0.5 * h)]
    ))
    best = ""
    for variant in variants:
        vh, vw = variant.shape[:2]
        for y in y_positions:
            text = _code39_decode_scanline(variant[y, :])
            if len(text) > len(best):
                best = text
                if len(best) >= 3:
                    # A serial-number scan can be validated by the caller;
                    # don't stop at short values because generic Code 39 may
                    # legitimately contain only a few characters.
                    pass
        if best:
            return best
    return ""


def _code39_rectified_decode(frame, barcode_detector=None):
    """Use OpenCV only to LOCATE a linear barcode, then decode its pixels
    ourselves. OpenCV does not have to understand Code 39 content."""
    if frame is None or not HAVE_CV2 or not HAVE_NUMPY:
        return ""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    if barcode_detector is None:
        return ""
    try:
        found, points = barcode_detector.detect(gray)
    except Exception:
        return ""
    if not found or points is None or len(points) == 0:
        return ""
    quad = np.asarray(points[0], dtype=np.float32)
    if quad.shape != (4, 2):
        return ""

    # Order corners around the quadrilateral.
    s = quad.sum(axis=1)
    d = np.diff(quad, axis=1).ravel()
    tl, br = quad[np.argmin(s)], quad[np.argmax(s)]
    tr, bl = quad[np.argmin(d)], quad[np.argmax(d)]
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    out_w = int(max(240, min(1800, round(max(width_a, width_b)))))
    out_h = int(max(60, min(600, round(max(height_a, height_b)))))
    if out_w <= out_h:
        # A Code 39 symbol is normally wider than tall.  If detector ordering
        # gives us a narrow box, enlarge the output canvas rather than losing
        # the bars to interpolation.
        out_w = max(out_w, out_h * 4)
    dst = np.array([[0, 0], [out_w - 1, 0],
                    [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    src = np.array([tl, tr, br, bl], dtype=np.float32)
    try:
        matrix = cv2.getPerspectiveTransform(src, dst)
        roi = cv2.warpPerspective(gray, matrix, (out_w, out_h),
                                   flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
    except cv2.error:
        return ""
    return _code39_decode_image(roi)

def _pyzbar_decode(frame):
    if not HAVE_PYZBAR:
        return ""
    try:
        # Prefer the raw frame first; then progressively processed variants.
        seen = set()
        for variant in _barcode_variants(frame):
            for code in pyzbar.decode(variant):
                try:
                    decoded = code.data.decode("utf-8", errors="ignore").strip()
                except Exception:
                    decoded = ""
                if decoded and decoded not in seen:
                    return decoded
                seen.add(decoded)
    except Exception:
        # A broken/missing native zbar DLL must never crash the application.
        return ""
    return ""


def decode_barcode_from_frame(frame, qr_detector=None, barcode_detector=None):
    """Decode QR/1-D barcodes without requiring administrator-installed ZBar.

    Order:
      1. pyzbar/ZBar when it is genuinely usable;
      2. built-in Code 39 decoder (works without ZBar/DLLs);
      3. OpenCV supported linear symbologies;
      4. QR detector.
    """
    text = _pyzbar_decode(frame)
    if text:
        return text

    # Code 39 is the important fallback for long alphanumeric unit serials.
    text = _code39_rectified_decode(frame, barcode_detector)
    if text:
        return text
    text = _code39_decode_image(frame)
    if text:
        return text

    if barcode_detector is not None:
        for variant in _barcode_variants(frame):
            try:
                ok, decoded_info, _decoded_type, _points = \
                    barcode_detector.detectAndDecodeWithType(variant)
                if ok:
                    for value in decoded_info:
                        if value:
                            return str(value)
            except (cv2.error, TypeError, ValueError):
                continue

    if qr_detector is not None:
        for variant in _barcode_variants(frame):
            try:
                data, _points, _straight = qr_detector.detectAndDecode(variant)
                if data:
                    return str(data)
            except (cv2.error, TypeError, ValueError):
                continue
    return ""


def _deskew_using_barcode(gray, barcode_detector):
    """Rotate the whole frame to straighten the barcode - the printed text
    above it is part of the same rigid label, so it shares the same tilt.
    Returns (image, corrected) - `image` is unchanged if nothing was found
    to measure the tilt from."""
    if barcode_detector is None:
        return gray, False
    try:
        found, points = barcode_detector.detect(gray)
    except cv2.error:
        return gray, False
    if not found:
        return gray, False

    quad = points[0]
    top_two = quad[np.argsort(quad[:, 1])[:2]]
    top_two = top_two[np.argsort(top_two[:, 0])]
    (x1, y1), (x2, y2) = top_two
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    deskewed = cv2.warpAffine(gray, matrix, (w, h), borderValue=255)
    return deskewed, True


def _locate_text_band(gray, barcode_detector):
    """Find the barcode, then crop the band directly above it - that's
    where the printed serial number lives on this label layout. Returns
    None if the barcode can't be located in this frame."""
    if barcode_detector is None:
        return None
    try:
        found, points = barcode_detector.detect(gray)
    except cv2.error:
        return None
    if not found:
        return None

    h, w = gray.shape
    ys = points[0][:, 1]
    barcode_top = int(max(0, ys.min()))
    band_height = int(barcode_top * 0.6)
    crop_top = max(0, barcode_top - band_height - 8)
    crop_bottom = max(crop_top + 1, barcode_top - 8)
    if crop_bottom - crop_top < 10:
        return None
    return gray[crop_top:crop_bottom, 0:w]


def _ocr_band(band_gray):
    """OCR one text band. Returns (candidate, raw_word, cleaned_token, conf):

    candidate      the validated 20-character A-Z0-9 result, or None
    raw_word       exactly what Tesseract returned for the best-matching
                   word, before any cleaning - for on-screen debugging
    cleaned_token  the same word after removing spaces/punctuation and
                   upper-casing, even if it isn't exactly 20 characters
    conf           Tesseract's own confidence for that word, 0-100

    Deliberately does NOT do blind character substitution (O->0, I->1,
    etc.) - only whitespace/punctuation stripping and upper-casing, per
    the project's requirement that corrections must be justified, not
    applied everywhere. A single PSM-6 pass on the upscaled band, picking
    the longest alphanumeric token, was found in testing to be more
    reliable than a second "tight crop" pass, which introduced its own
    errors right at the crop edges.
    """
    if not CAN_READ_SERIAL_TEXT:
        return None, "", "", 0

    up = cv2.resize(band_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    try:
        data = pytesseract.image_to_data(up, config="--psm 6",
                                         output_type=pytesseract.Output.DICT)
    except Exception:
        return None, "", "", 0

    best_raw, best_cleaned, best_len, best_conf = "", "", 0, 0
    for i, word in enumerate(data.get("text", [])):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", word).upper()
        if len(cleaned) > best_len:
            best_len = len(cleaned)
            best_raw = word
            best_cleaned = cleaned
            try:
                best_conf = max(0, int(data["conf"][i]))
            except (ValueError, TypeError):
                best_conf = 0

    candidate = best_cleaned if SERIAL_RE.fullmatch(best_cleaned) else None
    return candidate, best_raw, best_cleaned, best_conf


class StabilityTracker:
    """Requires a value to be seen `required` times in a row before it
    counts as accepted - a single good-looking frame is not enough for a
    QC record. Also remembers the last value that WAS accepted, so the
    same serial doesn't get processed over and over on every frame once
    it's already been used.
    """

    def __init__(self, required=3):
        self.required = required
        self.current = None      # this frame's raw candidate (may be None)
        self._streak_value = None
        self._streak = 0
        self.last_accepted = None

    def push(self, value):
        """Feed this frame's candidate (or None if nothing usable was
        read). Returns the value once it has been seen `required` times
        in a row, else None."""
        self.current = value
        if value is None:
            self._streak_value = None
            self._streak = 0
            return None
        if value == self._streak_value:
            self._streak += 1
        else:
            self._streak_value = value
            self._streak = 1
        return value if self._streak >= self.required else None

    def reset(self):
        self._streak_value = None
        self._streak = 0

    def mark_accepted(self, value):
        self.last_accepted = value
        self.reset()


class _CameraBase(tk.Toplevel):
    """Shared camera window with a preview that always fits on screen."""

    def __init__(self, parent, title, camera_index=0):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.transient(parent.winfo_toplevel())
        except Exception:
            pass

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # Leave enough vertical space for labels + action buttons.  The old
        # version displayed a 1280x720 frame at native size, which could put
        # Capture/Use/Cancel below the visible desktop on 1366x768 screens.
        self._preview_max_w = max(480, min(960, sw - 70))
        self._preview_max_h = max(300, min(540, sh - 270))

        self.cap = self._open_camera(camera_index)
        if self.cap is not None and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            try:
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except Exception:
                pass

        self._running = bool(self.cap is not None and self.cap.isOpened())
        self._imgtk = None
        self._last_frame = None

        self.video_label = tk.Label(self, bg="#000000")
        self.video_label.pack(padx=14, pady=(14, 8))

        if not self._running:
            self.video_label.configure(
                text=("Could not open a camera.\n\n"
                      "Check camera permissions, make sure the webcam is "
                      "connected, and close other programs using it."),
                fg="#FFFFFF", bg="#000000", font=(theme.FONT, 11),
                width=56, height=14)

        self.grab_set()
        self.lift()
        self.focus_force()

    @staticmethod
    def _open_camera(camera_index):
        """Try the Windows DirectShow backend first, then normal OpenCV."""
        indices = [camera_index] + [i for i in range(5) if i != camera_index]
        backends = []
        if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
            backends.append(cv2.CAP_DSHOW)
        if hasattr(cv2, "CAP_MSMF"):
            backends.append(cv2.CAP_MSMF)
        backends.append(cv2.CAP_ANY)

        for idx in indices:
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        return cap
                    cap.release()
                except Exception:
                    pass
        return None

    def _on_close(self):
        self._running = False
        if getattr(self, "cap", None) is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.destroy()

    def _read_frame(self):
        if not self._running or self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        return frame

    def _show_frame(self, frame_bgr):
        if not HAVE_PIL:
            return
        h, w = frame_bgr.shape[:2]
        scale = min(self._preview_max_w / w, self._preview_max_h / h, 1.0)
        if scale < 1.0:
            frame_bgr = cv2.resize(
                frame_bgr, (max(1, int(w * scale)), max(1, int(h * scale))),
                interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        self._imgtk = ImageTk.PhotoImage(image=image)
        self.video_label.configure(image=self._imgtk)


class PhotoCaptureDialog(_CameraBase):
    """Take a photo for one test, on the spot.

    After the dialog closes, `.saved_path` holds a temporary jpg file if the
    operator captured and accepted a photo, or None if they cancelled.
    """

    def __init__(self, parent, test_name, camera_index=0):
        super().__init__(parent, f"Camera - {test_name}", camera_index)
        self.saved_path = None
        self._frozen_frame = None

        tk.Label(self, text=f"Test: {test_name}", bg=theme.BG, fg=theme.INK,
                 font=(theme.FONT, 10, "bold")).pack(pady=(0, 4))
        self.hint = tk.Label(self, text="Line up the shot, then click Capture.",
                             bg=theme.BG, fg=theme.MUTED,
                             font=(theme.FONT, 9))
        self.hint.pack(pady=(0, 8))

        bar = tk.Frame(self, bg=theme.BG)
        bar.pack(pady=(0, 14))

        def mk(text, cmd, bg, state="normal"):
            b = tk.Button(bar, text=text, command=cmd, bg=bg, fg="#FFFFFF",
                         relief="flat", bd=0, font=(theme.FONT, 10, "bold"),
                         padx=16, pady=7, cursor="hand2", state=state,
                         activebackground=bg, disabledforeground="#FFFFFF")
            b.pack(side="left", padx=(0, 8))
            return b

        self.capture_btn = mk("Take picture", self._capture, theme.PRIMARY)
        self.retake_btn = mk("Retake", self._retake, theme.MUTED,
                             state="disabled")
        self.use_btn = mk("Use this photo", self._use, theme.OK_COLOR,
                          state="disabled")
        tk.Button(bar, text="Cancel", command=self._on_close, relief="flat",
                 bd=0, bg=theme.BG, fg=theme.INK, font=(theme.FONT, 10),
                 padx=12, pady=7, cursor="hand2").pack(side="left")

        self.bind("<Key>", self._on_key)
        self.bind("<Escape>", lambda _e: self._on_close())

        if self._running:
            self._tick()

    def _tick(self):
        if not self._running or self._frozen_frame is not None:
            return
        frame = self._read_frame()
        if frame is not None:
            self._show_frame(frame)
            self._last_frame = frame
        self.after(33, self._tick)

    def _capture(self):
        if self._last_frame is None:
            return
        self._frozen_frame = self._last_frame.copy()
        self._show_frame(self._frozen_frame)
        self.hint.configure(text="Photo captured. Click Use this photo or Retake.")
        self.capture_btn.configure(state="disabled")
        self.retake_btn.configure(state="normal")
        self.use_btn.configure(state="normal")

    def _on_key(self, event):
        if event.keysym in ("space", "Return") and self.capture_btn["state"] == "normal":
            self._capture()
            return "break"
        if event.keysym == "Escape":
            self._on_close()
            return "break"

    def _retake(self):
        self._frozen_frame = None
        self.hint.configure(text="Line up the shot, then click Capture.")
        self.capture_btn.configure(state="normal")
        self.retake_btn.configure(state="disabled")
        self.use_btn.configure(state="disabled")
        self._tick()

    def _use(self):
        if self._frozen_frame is None:
            return
        fd, path = tempfile.mkstemp(prefix="qc_capture_", suffix=".jpg")
        os.close(fd)
        cv2.imwrite(path, self._frozen_frame)
        self.saved_path = path
        self._on_close()


class ScanCaptureDialog(_CameraBase):
    """Read a QR code or 1D barcode from a webcam feed - barcode only, no
    OCR. Use VerifiedScanDialog instead for labels where the printed
    serial number should be cross-checked against the barcode.

    `.payload` holds the decoded text after the dialog closes, or None if
    cancelled or nothing was read.
    """

    def __init__(self, parent, prompt, camera_index=0):
        super().__init__(parent, "Scan with camera", camera_index)
        self.payload = None
        self._qr = cv2.QRCodeDetector()
        self._barcode = (cv2.barcode_BarcodeDetector()
                         if HAVE_CV2_BARCODE else None)

        tk.Label(self, text=prompt, bg=theme.BG, fg=theme.INK,
                font=(theme.FONT, 11, "bold"), wraplength=460,
                justify="left").pack(pady=(0, 6), padx=14)
        self.status = tk.Label(
            self, text="Point the camera at the code..." if self._running
                       else "", bg=theme.BG, fg=theme.MUTED,
            font=(theme.FONT, 9))
        self.status.pack(pady=(0, 10))

        if not CAN_READ_CODE39_FAMILY:
            warn_text = ("Code 39 camera decoding is unavailable because the "
                         "required camera/numeric components are missing. "
                         "Photo capture is unaffected.")
            tk.Label(self, text=warn_text, bg=theme.BG, fg=theme.RW_COLOR,
                    font=(theme.FONT, 8), wraplength=460,
                    justify="left").pack(pady=(0, 6), padx=14)

        tk.Button(self, text="Cancel", command=self._on_close, relief="flat",
                 bd=0, bg=theme.BG, fg=theme.INK, font=(theme.FONT, 10),
                 padx=12, pady=7, cursor="hand2").pack(pady=(0, 14))

        if self._running:
            self._tick()

    def _tick(self):
        if not self._running or self.payload is not None:
            return
        frame = self._read_frame()
        if frame is not None:
            self._show_frame(frame)
            self._try_decode(frame)
        self.after(40, self._tick)

    def _try_decode(self, frame):
        text = decode_barcode_from_frame(frame, self._qr, self._barcode)
        if text:
            self.payload = text
            self.status.configure(text="Code found.", fg=theme.OK_COLOR)
            self.after(200, self._on_close)


class VerifiedScanDialog(_CameraBase):
    """Read the printed serial number above the barcode via OCR, decode the
    barcode too, and cross-check the two against each other. Neither
    method is trusted alone: a value only counts once the SAME reading has
    shown up on several consecutive frames, and OCR/barcode must agree
    (unless one of the two methods isn't installed at all, in which case
    it falls back to the other one alone rather than blocking forever).

    Use this for the primary unit-serial scan step; use ScanCaptureDialog
    for simpler codes that don't have a printed human-readable twin to
    check against.

    `.payload` holds the verified 20-character serial after the dialog
    closes with a PASS, or None if cancelled.
    """

    PROCESS_INTERVAL_MS = 450
    PREVIEW_INTERVAL_MS = 33
    STABILITY_FRAMES = 3
    STUCK_AFTER_TICKS = 20

    def __init__(self, parent, prompt, camera_index=0):
        super().__init__(parent, "Verify serial number (OCR + barcode)",
                         camera_index)
        self.payload = None
        self._qr = cv2.QRCodeDetector() if HAVE_CV2 else None
        self._barcode = cv2.barcode_BarcodeDetector() if HAVE_CV2_BARCODE else None
        self._ocr_tracker = StabilityTracker(self.STABILITY_FRAMES)
        self._barcode_tracker = StabilityTracker(self.STABILITY_FRAMES)
        self._no_read_streak = 0
        self._barcode_stable_wait = 0
        self._latest_frame = None

        tk.Label(self, text=prompt, bg=theme.BG, fg=theme.INK,
                font=(theme.FONT, 11, "bold"), wraplength=640,
                justify="left").pack(pady=(0, 8), padx=14)

        if not CAN_READ_SERIAL_TEXT:
            tk.Label(self, text="OCR isn't set up (Tesseract not found) - "
                                "only the barcode will be checked. See "
                                "Tools > Camera diagnostics for details.",
                     bg=theme.BG, fg=theme.RW_COLOR, font=(theme.FONT, 8),
                     wraplength=640, justify="left").pack(pady=(0, 4), padx=14)
        if not CAN_READ_CODE39_FAMILY:
            tk.Label(self, text="Code 39 camera decoding is unavailable. "
                                "See Tools > Camera diagnostics.",
                     bg=theme.BG, fg=theme.RW_COLOR, font=(theme.FONT, 8),
                     wraplength=640, justify="left").pack(pady=(0, 6), padx=14)

        grid = tk.Frame(self, bg=theme.BG)
        grid.pack(fill="x", padx=20, pady=(4, 6))
        grid.columnconfigure(0, weight=1, uniform="col")
        grid.columnconfigure(1, weight=1, uniform="col")

        def make_readout(label_text):
            box = tk.Frame(grid, bg=theme.SURFACE,
                           highlightbackground=theme.BORDER,
                           highlightthickness=1)
            tk.Label(box, text=label_text, bg=theme.SURFACE, fg=theme.MUTED,
                    font=(theme.FONT, 9, "bold")).pack(anchor="w",
                                                       padx=10, pady=(8, 0))
            value = tk.Label(box, text="...", bg=theme.SURFACE, fg=theme.INK,
                             font=("Consolas", 15, "bold"), anchor="w")
            value.pack(anchor="w", padx=10, pady=(0, 2), fill="x")
            return box, value

        ocr_box, self.ocr_value = make_readout("OCR SERIAL")
        ocr_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=4)
        self.ocr_conf_label = tk.Label(ocr_box, text="OCR CONFIDENCE: -",
                                       bg=theme.SURFACE, fg=theme.MUTED,
                                       font=(theme.FONT, 8))
        self.ocr_conf_label.pack(anchor="w", padx=10, pady=(0, 8))

        barcode_box, self.barcode_value = make_readout("BARCODE SERIAL")
        barcode_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=4)
        tk.Label(barcode_box, text=" ", bg=theme.SURFACE,
                font=(theme.FONT, 8)).pack(anchor="w", padx=10, pady=(0, 8))

        self.result_label = tk.Label(self, text="SCANNING...", bg=theme.BG,
                                     fg=theme.MUTED,
                                     font=(theme.FONT, 26, "bold"))
        self.result_label.pack(pady=(12, 4))

        self.detail_label = tk.Label(self, text="", bg=theme.BG,
                                     fg=theme.MUTED, font=(theme.FONT, 9),
                                     wraplength=640, justify="left")
        self.detail_label.pack(pady=(0, 10), padx=14)

        bar = tk.Frame(self, bg=theme.BG)
        bar.pack(pady=(0, 14))
        tk.Button(bar, text="Accept current reading", command=self._manual_accept,
                 relief="flat", bd=0, bg=theme.MUTED, fg="#FFFFFF",
                 font=(theme.FONT, 9, "bold"), padx=12, pady=6,
                 cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(bar, text="Cancel", command=self._on_close, relief="flat",
                 bd=0, bg=theme.BG, fg=theme.INK, font=(theme.FONT, 10),
                 padx=12, pady=7, cursor="hand2").pack(side="left")

        self.bind("<Key>", self._on_key)
        self.bind("<Escape>", lambda _e: self._on_close())

        if self._running:
            self._preview_tick()
            self.after(self.PROCESS_INTERVAL_MS, self._process_tick)

    def _preview_tick(self):
        if not self._running or self.payload is not None:
            return
        frame = self._read_frame()
        if frame is not None:
            self._show_frame(frame)
            self._latest_frame = frame
        self.after(self.PREVIEW_INTERVAL_MS, self._preview_tick)

    def _process_tick(self):
        if not self._running or self.payload is not None:
            return
        frame = self._latest_frame
        if frame is None:
            self.after(self.PROCESS_INTERVAL_MS, self._process_tick)
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        ocr_candidate, ocr_raw, ocr_cleaned, ocr_conf = None, "", "", 0
        if CAN_READ_SERIAL_TEXT:
            deskewed, _ = _deskew_using_barcode(gray, self._barcode)
            band = _locate_text_band(deskewed, self._barcode)
            if band is not None:
                ocr_candidate, ocr_raw, ocr_cleaned, ocr_conf = _ocr_band(band)

        barcode_text = decode_barcode_from_frame(frame, self._qr, self._barcode)
        barcode_candidate = None
        if barcode_text:
            cleaned = re.sub(r"[^A-Za-z0-9]", "", barcode_text).upper()
            if SERIAL_RE.fullmatch(cleaned):
                barcode_candidate = cleaned

        stable_ocr = self._ocr_tracker.push(ocr_candidate)
        stable_barcode = self._barcode_tracker.push(barcode_candidate)

        self.ocr_value.configure(
            text=ocr_candidate or ocr_cleaned or "NOT DETECTED",
            fg=theme.OK_COLOR if ocr_candidate else theme.MUTED)
        self.ocr_conf_label.configure(text=f"OCR CONFIDENCE: {ocr_conf}%")
        self.barcode_value.configure(
            text=barcode_candidate or (barcode_text.strip().upper()
                                       if barcode_text else "NOT DETECTED"),
            fg=theme.OK_COLOR if barcode_candidate else theme.MUTED)

        if stable_ocr and stable_barcode:
            if stable_ocr == stable_barcode:
                self._accept(stable_ocr, "OCR and barcode agree.")
            else:
                self.result_label.configure(text="MISMATCH", fg=theme.NG_COLOR)
                self.detail_label.configure(
                    text=f"OCR reads {stable_ocr!r} but the barcode reads "
                         f"{stable_barcode!r}. Reposition the label; neither "
                         "value was accepted.")
                self._ocr_tracker.reset()
                self._barcode_tracker.reset()
                self._barcode_stable_wait = 0
            self._no_read_streak = 0
        elif stable_barcode:
            # Barcode decoding is the authoritative machine-readable value.
            # If OCR is installed but cannot locate the printed text (a common
            # case with Code-39 labels), the old version could wait forever.
            # Give OCR a short chance to agree, then accept the stable barcode.
            self._barcode_stable_wait += 1
            if not CAN_READ_SERIAL_TEXT or self._barcode_stable_wait >= 6:
                self._accept(
                    stable_barcode,
                    "Barcode reading is stable. "
                    + ("OCR did not produce a valid reading, so the barcode "
                       "value was accepted." if CAN_READ_SERIAL_TEXT
                       else "OCR is not available; barcode used."))
            else:
                self.result_label.configure(
                    text="BARCODE STABLE", fg=theme.OK_COLOR)
                self.detail_label.configure(
                    text="Barcode is stable. Waiting briefly for OCR "
                         "confirmation; keep the label steady.")
        elif stable_ocr and not CAN_READ_CODE39_FAMILY:
            self._accept(stable_ocr,
                        "Barcode reader unavailable - accepted from OCR alone.")
        elif ocr_candidate is None and barcode_candidate is None:
            self._barcode_stable_wait = 0
            self._no_read_streak += 1
            if self._no_read_streak >= self.STUCK_AFTER_TICKS:
                self.result_label.configure(text="RESCAN", fg=theme.RW_COLOR)
                self.detail_label.configure(
                    text="Neither method is reading a code. Reposition the "
                         "label so it fills more of the frame, hold it "
                         "flat and steady, and check the lighting.")
            else:
                self.result_label.configure(text="SCANNING...", fg=theme.MUTED)
        else:
            self._barcode_stable_wait = 0
            self._no_read_streak = 0
            self.result_label.configure(text="SCANNING...", fg=theme.MUTED)
            self.detail_label.configure(text="")

        self.after(self.PROCESS_INTERVAL_MS, self._process_tick)

    def _accept(self, value, reason):
        self._ocr_tracker.mark_accepted(value)
        self._barcode_tracker.mark_accepted(value)
        self.result_label.configure(text="PASS", fg=theme.OK_COLOR)
        self.detail_label.configure(text=reason)
        self.payload = value
        self.after(500, self._on_close)

    def _manual_accept(self):
        """Let the operator accept whichever single reading currently on
        screen looks right, for the rare case both methods are struggling
        but a human can see the value is correct. Requires at least a
        properly-formatted 20-character reading from one of the two."""
        candidates = [c for c in (self._ocr_tracker.current,
                                  self._barcode_tracker.current) if c]
        if not candidates:
            messagebox.showinfo(
                "Nothing to accept yet",
                "Neither method has a valid-looking reading right now.",
                parent=self)
            return
        self._accept(candidates[0], "Accepted manually by the operator.")
