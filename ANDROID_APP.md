# Quality Cross-Check System — Android App & APK

A native Android application built with **Jetpack Compose**, **Kotlin Coroutines**, and **Material 3**, replicating the complete functional architecture, industrial design, security, and verification workflows of the desktop Quality Cross-Check System (`qc_system`).

---

## 📱 Quick Access: Ready-to-Install APK

The compiled Android application package is ready for direct installation:

- **Workspace Root APK**: [`qc_system_android.apk`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/qc_system_android.apk) (29.3 MB)
- **Gradle Build Output**: [`android_app/app/build/outputs/apk/debug/app-debug.apk`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/build/outputs/apk/debug/app-debug.apk)

### How to Install

#### Option 1: Via ADB (Android Debug Bridge)
If your phone, tablet, or industrial barcode terminal is connected via USB with Developer Mode / USB Debugging enabled:
```powershell
adb install -r qc_system_android.apk
```

#### Option 2: Direct USB Transfer / Sideloading
1. Copy `qc_system_android.apk` to your Android device via USB cable, Google Drive, WhatsApp, or local network share.
2. On your device, tap the APK in the Files app.
3. Allow **"Install from unknown sources"** when prompted, then tap **Install**.

---

## 🚀 Key Features & Full Parity with Desktop System

### 1. 🔐 Role-Based Authentication & Security
- **PBKDF2-HMAC-SHA256**: Same cryptographic standard (200,000 iterations, 16-byte random salt, constant-time verification) compatible with desktop credential hashes.
- **Role Permissions**:
  - `inspector`: Check sheet selection, unit details scanning, test execution, mandatory photo capture, and record submission.
  - `admin`: Full inspector access + **Check Sheet Builder** (live no-code editor) and historical record audits.
- **Default Accounts**:
  - Admin: `admin` / `admin123`
  - Inspector: `inspector` / `qc123`

### 2. 📋 Check Sheet Selection
- Direct selection between factory stations: **OQC** (Outgoing Quality Control), **AUDIT** (Audit Inspection), **IQC** (Incoming Quality Control), or custom sheets created via Builder.
- Station metadata displayed: test count, required fields, and sequential scan targets.

### 3. 🔍 Industrial Sequential Barcode Engine
- Sequential scanning step-by-step with status indicators (`WAITING`, `SCANNED`, `ERROR`).
- **All 6 Scanning Parse Modes Supported**:
  1. `raw`: Direct mapping from barcode to unit field.
  2. `delimited`: Splitting by custom separator (`|`, `,`, `-`, etc.) and selecting by token index.
  3. `split`: Key-value pair splitting (e.g., `SN:12345`).
  4. `regex`: Regular expression pattern matching with capture groups.
  5. `json`: JSON object extraction by key.
  6. `fixed`: Substring slice extraction by start and end character indexes.
- **Camera Barcode Reader**: Built-in ZXing camera barcode engine for scanning physical 1D/2D barcodes directly with the device's camera.
- **Manual Input Fallback**: Inspectors can manually type codes if a physical label is damaged.

### 4. 🧪 Test Matrix & Enforced Verification
- Interactive test items with **OK (Pass)**, **NG (Defect)**, and **RW (Rework)** buttons.
- **Mandatory Photo Capture Requirement**: Enforces that at least one photo is taken before any test item can be marked with a result status, preventing bypassed inspections.
- **Defect Note Dialog**: Whenever an item is marked **NG** or **RW**, a modal prompts the inspector for the defect root cause / observation note.
- **Duplicate Inspection Safeguard**: If an existing record with the same check sheet and serial number is detected, the inspector is prompted whether to update the existing record or cancel.
- **Visual Progress Bar & Counter**: Real-time ratio of completed items, pass/fail/rework tallies, and submit gate.

### 5. 📷 Native High-Resolution Photo Capture
- Integrated with Android's system camera via `FileProvider` (`androidx.core.content.FileProvider`).
- High-resolution uncompressed photo capture saved to the app's sandboxed external photos directory (`files/photos/`).
- Fullscreen zoom preview dialog with tap-to-close.

### 6. 🛠️ No-Code Check Sheet Builder (Admin Only)
- **General Tab**: Edit check sheet name, description, and status.
- **Unit Fields Tab**: Add, edit, reorder, and configure mandatory/optional fields.
- **Tests Tab**:
  - Add individual tests, edit test names, and reorder inspection sequence.
  - **Excel Bulk Paste**: Paste test lists directly from spreadsheets. Automatically cleans leading numbers (`1.`, `2)`) and formatting.
- **Scanning Rules Tab**: Configure sequential scan steps with target field mappings and parse rules.
- **Rule Testing Sandbox**: Built-in simulation sandbox where admins can type test barcode strings and immediately verify if the parsing rule extracts the expected field.
- **Rolling Backups**: Automatically creates timestamped JSON backups in `backups/` whenever changes are saved.

### 7. 📊 Historical Records & Audit Viewer
- Full inspection audit trail stored locally in SQLite (`qc_system.db`).
- Filter by date, check sheet type, or search by serial number / main board number.
- High-level metric summary cards: Total Inspected, OK Count, NG Count, Rework Count.
- Tap any record to inspect individual test items, defect notes, timestamps, inspector name, and captured photos.

---

## 🎨 Industrial Design System

The Android app faithfully adopts the desktop application's industrial aesthetic:
- **Primary Navy**: `#1D4E89`
- **Dark Steel Header**: `#14202B`
- **Factory Surface**: `#EEF1F4`
- **Card Background**: `#FFFFFF`
- **Pass (OK) Green**: `#1B8A4B`
- **Fail (NG) Red**: `#C0392B`
- **Rework (RW) Amber**: `#D98200`
- **Borders & Dividers**: `#CFD8DC`

---

## 🏗️ Technical Architecture

```
android_app/
├── app/
│   ├── build.gradle.kts             # Dependencies (Compose, ZXing, Kotlin Serialization)
│   ├── src/
│   │   ├── main/
│   │   │   ├── AndroidManifest.xml   # Camera permissions, FileProvider configuration
│   │   │   ├── java/com/example/qcsystem/
│   │   │   │   ├── MainActivity.kt          # Single-activity lifecycle host
│   │   │   │   ├── Navigation.kt            # Screen routing & state transitions
│   │   │   │   ├── NavigationKeys.kt        # Type-safe navigation routes
│   │   │   │   ├── auth/AuthManager.kt      # PBKDF2-HMAC-SHA256 authentication
│   │   │   │   ├── data/
│   │   │   │   │   ├── AppDatabase.kt       # SQLite helper, transactions & duplicates
│   │   │   │   │   └── DataRepository.kt    # Check sheet seeding, backups, photos
│   │   │   │   ├── model/Models.kt          # Data contracts (Checksheet, UnitField, etc.)
│   │   │   │   ├── scanner/ScanningEngine.kt # 6 parse rules & ZXing barcode engine
│   │   │   │   ├── theme/
│   │   │   │   │   ├── Color.kt             # QC industrial color palette
│   │   │   │   │   └── Theme.kt             # Material 3 typography & styling
│   │   │   │   └── ui/
│   │   │   │       ├── builder/BuilderScreen.kt # Visual no-code check sheet editor
│   │   │   │       ├── components/CommonComponents.kt # Header, badges, cards
│   │   │   │       └── screens/
│   │   │   │           ├── LoginScreen.kt       # Inspector & admin authentication
│   │   │   │           ├── SelectScreen.kt      # Check sheet picker & admin switcher
│   │   │   │           ├── DetailsScreen.kt     # Sequential barcode scanner screen
│   │   │   │           ├── ChecksheetScreen.kt  # Test matrix & photo verification
│   │   │   │           └── RecordsScreen.kt     # Audit logs, search & filter
│   │   │   └── res/
│   │   │       ├── values/strings.xml
│   │   │       └── xml/file_paths.xml       # FileProvider path mappings
│   │   └── test/java/com/example/qcsystem/
│   │       └── ScanningEngineTest.kt        # Unit tests for barcode rules & hashing
├── build.gradle.kts
├── settings.gradle.kts
└── gradlew.bat
```

---

## 🛠️ Rebuilding from Source

To compile the Android app from source on Windows:
```powershell
cd android_app
cmd /c "gradlew.bat test assembleDebug"
```
The output APK will be generated at `app/build/outputs/apk/debug/app-debug.apk`.
