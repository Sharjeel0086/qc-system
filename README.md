# Quality Cross-Check System (QC System)

An industrial-grade, dual-platform quality assurance system built for manufacturing and assembly lines (LED TV, consumer electronics, and appliance fabrication). The repository contains two synchronized implementations sharing the same cryptographic security, data contracts, and verification logic:

1. **Native Android Application** (`android_app/`): Built with **Kotlin 2.3**, **Jetpack Compose (Material 3)**, **ZXing Barcode Engine**, **Android Camera FileProvider**, and **SQLite**. Ideal for portable industrial barcode terminals (Zebra, Honeywell, etc.), tablets, and inspection smartphones.
2. **Desktop Workstation Application**: Built with **Python 3**, **Tkinter**, **SQLite**, and an advanced computer vision pipeline (**OpenCV**, **Tesseract OCR**, and a standalone **Code 39 pixel-pattern decoder**). Ideal for stationary test benches and workstation PCs.

---

## 📑 Table of Contents

- [Quality Cross-Check System (QC System)](#quality-cross-check-system-qc-system)
  - [📑 Table of Contents](#-table-of-contents)
  - [🌟 System Highlights \& Capabilities](#-system-highlights--capabilities)
  - [🗂️ Repository Architecture \& Directory Layout](#️-repository-architecture--directory-layout)
  - [📱 Android Application: Setup \& APK Creation](#-android-application-setup--apk-creation)
    - [1. Quick Installation: Pre-compiled APK](#1-quick-installation-pre-compiled-apk)
    - [2. Prerequisites for Android Development](#2-prerequisites-for-android-development)
    - [3. Compiling and Building the APK from Source](#3-compiling-and-building-the-apk-from-source)
    - [4. Generating a Signed Production Release APK](#4-generating-a-signed-production-release-apk)
  - [🛠️ Developer Guide: How to Make Changes in the Android App](#️-developer-guide-how-to-make-changes-in-the-android-app)
    - [Android Architecture Overview](#android-architecture-overview)
    - [Module \& Package Walkthrough](#module--package-walkthrough)
    - [Practical Change Recipes](#practical-change-recipes)
      - [Recipe 1: Customizing Colors and Industrial Theme](#recipe-1-customizing-colors-and-industrial-theme)
      - [Recipe 2: Modifying Data Models and Adding Unit Fields](#recipe-2-modifying-data-models-and-adding-unit-fields)
      - [Recipe 3: Updating the SQLite Database Schema \& Migrations](#recipe-3-updating-the-sqlite-database-schema--migrations)
      - [Recipe 4: Adding or Modifying Barcode Scanning Rules](#recipe-4-adding-or-modifying-barcode-scanning-rules)
      - [Recipe 5: Adding a New Screen and Navigation Route](#recipe-5-adding-a-new-screen-and-navigation-route)
      - [Recipe 6: Modifying Camera Settings \& Photo Capture FileProvider](#recipe-6-modifying-camera-settings--photo-capture-fileprovider)
      - [Recipe 7: Changing Default Users, Passwords, or Cryptographic Salt](#recipe-7-changing-default-users-passwords-or-cryptographic-salt)
      - [Recipe 8: Updating Version Code, Version Name, or Package Name](#recipe-8-updating-version-code-version-name-or-package-name)
      - [Recipe 9: Running Unit Tests \& Verifying Integrity](#recipe-9-running-unit-tests--verifying-integrity)
  - [💻 Desktop Application: Setup \& Execution](#-desktop-application-setup--execution)
    - [Quick Launch (Zero Setup Required)](#quick-launch-zero-setup-required)
    - [Optional Camera, Barcode \& OCR Requirements](#optional-camera-barcode--ocr-requirements)
  - [🔄 End-to-End Inspection Workflow](#-end-to-end-inspection-workflow)
  - [🔍 Barcode Parsing Engine (6 Modes)](#-barcode-parsing-engine-6-modes)
  - [🗄️ Database Schema \& Data Integrity](#️-database-schema--data-integrity)
  - [🔐 Security Model](#-security-model)
  - [❓ Troubleshooting \& FAQ](#-troubleshooting--faq)
  - [📄 License \& Credits](#-license--credits)

---

## 🌟 System Highlights & Capabilities

- **Role-Based Access Control**:
  - `inspector`: Check sheet selection, sequential unit scanning, test execution, mandatory photo capture, and record submission.
  - `admin`: All inspector rights + live visual **Check Sheet Builder** and full historical record auditing.
  - **Default Credentials**:
    - Administrator: `admin` / `admin123`
    - Inspector: `inspector` / `qc123`
- **6-Mode Universal Barcode Parsing Engine**:
  - Decode raw codes, custom-delimited strings, index splits, JSON payloads, regular expressions, and fixed-character substring slices.
- **Enforced Quality Verification Gates**:
  - **Mandatory Photo Gate**: Test items cannot be marked OK, NG, or RW without an uncompressed photo snapshot.
  - **Defect Root-Cause Reason Gate**: Marking an item NG or RW enforces a prompt requiring an observation/reason note.
  - **Duplicate Inspection Safeguard**: Detects prior runs on the same serial number and warns the operator before overwriting.
- **No-Code Visual Check Sheet Builder**:
  - Create, clone, and configure check sheets live.
  - Supports **Excel bulk paste** (paste entire columns from spreadsheets with automatic cleanup of leading numbers like `1.`, `2)`).
  - Built-in **Rule Testing Sandbox** to preview barcode parsing on live strings before saving.
  - **Automatic rolling backups** saved to `backups/` on every save.
- **Hardware Agnostic**:
  - Works with standard USB handheld scanners (acting as keyboard wedges), smartphone/tablet cameras via ZXing / OpenCV, or industrial barcode terminals.

---

## 🗂️ Repository Architecture & Directory Layout

```
qc_system/
├── qc_system_android.apk             # Compiled, ready-to-install Android APK (29.3 MB)
├── ANDROID_APP.md                    # Android feature guide and mobile documentation
├── README.md                         # This comprehensive repository guide
│
├── android_app/                      # Native Android Kotlin + Jetpack Compose project
│   ├── build.gradle.kts              # Root Gradle build script
│   ├── settings.gradle.kts           # Module definitions and repository settings
│   ├── gradle.properties             # JVM arguments & AndroidX configuration
│   ├── gradlew / gradlew.bat         # Gradle wrapper executables (Unix / Windows)
│   ├── gradle/
│   │   ├── wrapper/                  # Gradle 9.0 wrapper binaries
│   │   └── libs.versions.toml        # Version Catalog (Dependencies & plugins)
│   └── app/
│       ├── build.gradle.kts          # App-level dependencies, SDK targets, signing
│       ├── proguard-rules.pro        # ProGuard / R8 code shrinking rules
│       └── src/
│           ├── main/
│           │   ├── AndroidManifest.xml # Permissions (CAMERA) & FileProvider mapping
│           │   ├── java/com/example/qcsystem/
│           │   │   ├── MainActivity.kt          # Single-activity lifecycle container
│           │   │   ├── Navigation.kt            # Compose Navigation 3 screen routing
│           │   │   ├── NavigationKeys.kt        # Type-safe navigation destination keys
│           │   │   ├── auth/
│           │   │   │   └── AuthManager.kt       # PBKDF2-HMAC-SHA256 password hashing
│           │   │   ├── data/
│           │   │   │   ├── AppDatabase.kt       # SQLiteOpenHelper schema, queries & index
│           │   │   │   └── DataRepository.kt    # Checksheet JSON, backups & photo management
│           │   │   ├── model/
│           │   │   │   └── Models.kt            # Data contracts (Checksheet, UnitField, etc.)
│           │   │   ├── scanner/
│           │   │   │   └── ScanningEngine.kt    # 6-mode parsing rules & ZXing barcode engine
│           │   │   ├── theme/
│           │   │   │   ├── Color.kt             # QC industrial color palette
│           │   │   │   └── Theme.kt             # Material 3 typography & theme container
│           │   │   └── ui/
│           │   │       ├── builder/
│           │   │       │   └── BuilderScreen.kt # Live no-code check sheet builder UI
│           │   │       ├── components/
│           │   │       │   └── CommonComponents.kt # Headers, status badges, buttons, cards
│           │   │       └── screens/
│           │   │           ├── LoginScreen.kt       # Authentication screen
│           │   │           ├── SelectScreen.kt      # Check sheet selector & mode switcher
│           │   │           ├── DetailsScreen.kt     # Sequential barcode scanner screen
│           │   │           ├── ChecksheetScreen.kt  # Test matrix, photo gate & submission
│           │   │           └── RecordsScreen.kt     # Historical audit viewer & search
│           │   └── res/
│           │       ├── values/strings.xml
│           │       └── xml/file_paths.xml       # FileProvider external path declarations
│           └── test/java/com/example/qcsystem/
│               └── ScanningEngineTest.kt        # Unit tests for barcode rules & hashing
│
├── app.py                            # Desktop app entry point (Python/Tkinter)
├── auth.py                           # Desktop PBKDF2 password hashing
├── database.py                       # Desktop SQLite schema and query manager
├── config_loader.py                  # Desktop checksheets.json validator & loader
├── scanning.py                       # Desktop barcode parse engine
├── camera.py                         # Desktop OpenCV webcam, Code 39 & Tesseract OCR
├── theme.py                          # Desktop color palette and UI styles
├── widgets.py                        # Desktop scrollable frames and UI components
├── requirements.txt                  # Python dependencies (opencv-python, pillow, etc.)
├── Run QC System.bat                 # One-click Windows runner
├── Run QC System (no console).bat    # Silent runner without console window
├── Create Desktop Shortcut.bat       # Creates desktop icon
├── Install Camera Requirements.bat   # One-click setup for OpenCV/Tesseract
├── screens/                          # Desktop screen modules
│   ├── login_screen.py
│   ├── select_screen.py
│   ├── details_screen.py
│   ├── checksheet_screen.py
│   ├── records_screen.py
│   └── builder_screen.py
├── data/                             # Desktop storage directory
│   ├── checksheets.json              # Active check sheet definitions
│   ├── qc_system.db                  # Desktop SQLite database
│   └── backups/                      # Rolling check sheet JSON backups
└── photos/                           # Captured inspection photos storage
```

---

## 📱 Android Application: Setup & APK Creation

The Android application is a native mobile/tablet implementation designed to run completely offline on factory floors.

### 1. Quick Installation: Pre-compiled APK

A production-ready debug APK is pre-built and committed directly to the repository root:
- **Location**: [`qc_system_android.apk`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/qc_system_android.apk) (approx. 29.3 MB)

#### Method A: Install via ADB (Recommended for Industrial Handhelds & Tablets)
Connect your device to your development computer via USB with **USB Debugging** enabled:
```powershell
# Verify device connection
adb devices

# Install APK, replacing any existing installation (-r)
adb install -r qc_system_android.apk
```

#### Method B: Direct Sideloading (Phone / Tablet)
1. Transfer `qc_system_android.apk` to your Android device via USB, Google Drive, SD Card, or local network share.
2. Open the **Files** app on your Android device and tap `qc_system_android.apk`.
3. If prompted, toggle **"Allow from this source"** in device security settings.
4. Tap **Install** and launch **QC System**.

---

### 2. Prerequisites for Android Development

To modify the code or rebuild the APK from source, ensure your environment meets the following requirements:

| Tool | Minimum Version | Recommended / Configured Version | Notes |
|---|---|---|---|
| **JDK (Java Development Kit)** | JDK 17 | JDK 17 (Azul Zulu, Eclipse Temurin, or Oracle) | JVM Toolchain is configured to `JavaVersion.VERSION_17` in `build.gradle.kts`. |
| **Android SDK Platform** | API Level 34 | API Level 36 (`compileSdk = 36`) | Installed via Android Studio SDK Manager or `sdkmanager` CLI. |
| **Android Build Tools** | 34.0.0+ | 36.0.0+ | Required for compilation. |
| **Minimum Device OS** | Android 7.0 (API 24) | Android 10+ (API 29+) | Supports 95%+ of all active industrial devices. |
| **Android Studio** | Hedgehog (2023.1.1) | Ladybug / Meerkat (2024.2+) | Optional, but recommended for visual editing and emulator testing. |

#### Verifying Environment Variables on Windows:
Ensure `JAVA_HOME` and `ANDROID_HOME` are set in your environment:
```powershell
# Check Java
java -version

# Check JAVA_HOME
$env:JAVA_HOME

# Check ANDROID_HOME (or ANDROID_SDK_ROOT)
$env:ANDROID_HOME
# Example standard path: C:\Users\<Username>\AppData\Local\Android\Sdk
```

---

### 3. Compiling and Building the APK from Source

All build tasks use the Gradle wrapper inside the `android_app/` directory:

#### Step 1: Open Terminal in the Android Project Directory
```powershell
cd c:\Users\Muhammad Sharjeel\Downloads\qc_system\android_app
```

#### Step 2: Clean Previous Artifacts (Optional)
```powershell
cmd /c "gradlew.bat clean"
```

#### Step 3: Run Unit Tests
Validate barcode parsing algorithms and cryptographic hashing before building:
```powershell
cmd /c "gradlew.bat test"
```

#### Step 4: Assemble the Debug APK
```powershell
cmd /c "gradlew.bat assembleDebug"
```
Once the build completes with `BUILD SUCCESSFUL`, the compiled APK will be located at:
```
android_app/app/build/outputs/apk/debug/app-debug.apk
```

#### Step 5: Install Directly to Connected Device
```powershell
cmd /c "gradlew.bat installDebug"
```

---

### 4. Generating a Signed Production Release APK

To distribute the app to production workers without using debug keys, generate a signed release APK:

#### Step A: Generate a Keystore (One-Time Setup)
Run the Java `keytool` utility to create a cryptographic signing key:
```powershell
keytool -genkey -v -keystore qc-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias qckey
```
Store `qc-release-key.jks` in a secure location (e.g., inside `android_app/app/keystore/`).

#### Step B: Configure Signing in `android_app/app/build.gradle.kts`
Open [`android_app/app/build.gradle.kts`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/build.gradle.kts) and configure the `signingConfigs` block:

```kotlin
android {
    ...
    signingConfigs {
        create("release") {
            storeFile = file("keystore/qc-release-key.jks")
            storePassword = System.getenv("QC_KEYSTORE_PASSWORD") ?: "YourStorePassword"
            keyAlias = "qckey"
            keyPassword = System.getenv("QC_KEY_PASSWORD") ?: "YourKeyPassword"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

#### Step C: Build the Release APK
```powershell
cmd /c "gradlew.bat assembleRelease"
```
The output will be generated at:
```
android_app/app/build/outputs/apk/release/app-release.apk
```

---

## 🛠️ Developer Guide: How to Make Changes in the Android App

This section provides a complete guide for engineers modifying UI layouts, data contracts, barcode rules, or database schemas.

### Android Architecture Overview

The Android application follows modern **Unidirectional Data Flow (UDF)** and **Single-Activity Architecture**:

- **Activity Container**: [`MainActivity.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/MainActivity.kt) initializes the repository and sets up the root Jetpack Compose theme surface with edge-to-edge system bars.
- **Routing & Navigation**: [`Navigation.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/Navigation.kt) leverages **Navigation 3** with strongly typed destination keys defined in [`NavigationKeys.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/NavigationKeys.kt).
- **Data & Persistence**:
  - [`AppDatabase.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt): Manages the SQLite database (`qc_system.db`), handles transactions, and performs indexed lookups for inspections and test results.
  - [`DataRepository.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/DataRepository.kt): Manages reactive state (`StateFlow`), handles JSON serialization of check sheets, performs timestamped backups, and manages photo file storage.
- **Scanning Engine**: [`ScanningEngine.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/scanner/ScanningEngine.kt): Pure Kotlin engine handling all 6 barcode parsing rules, regular expressions, and ZXing bitmap decoding.
- **Design System**: [`Color.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Color.kt) and [`Theme.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Theme.kt): Custom industrial styling adhering to factory workstation ergonomics.

---

### Module & Package Walkthrough

| Package / File | Purpose | When to Modify |
|---|---|---|
| [`MainActivity.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/MainActivity.kt) | Application entry point and lifecycle host. | When configuring window insets, system splash screens, or global DI container. |
| [`NavigationKeys.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/NavigationKeys.kt) | Defines type-safe `NavKey` objects. | When adding a new screen route or passing new parameters between screens. |
| [`Navigation.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/Navigation.kt) | Maps navigation keys to composable screens and manages backstack transitions. | When linking a new screen into the user flow or modifying screen transitions. |
| [`model/Models.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/model/Models.kt) | Core data classes (`Checksheet`, `UnitField`, `TestItem`, `Inspection`, `User`). | When adding fields to inspections, check sheets, or user profiles. |
| [`data/AppDatabase.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt) | Raw SQLite queries, schema creation, duplicate record detection. | When altering SQLite tables, adding new indices, or writing custom analytics queries. |
| [`data/DataRepository.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/DataRepository.kt) | Check sheet JSON I/O, automatic rolling backups, photo saving, and active session cache. | When changing how photos are stored or check sheet JSON validation rules. |
| [`scanner/ScanningEngine.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/scanner/ScanningEngine.kt) | Barcode parsing algorithms and ZXing Camera frame decoders. | When introducing new barcode formats, custom token delimiters, or fixing regex extraction. |
| [`auth/AuthManager.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/auth/AuthManager.kt) | PBKDF2-HMAC-SHA256 password hashing and validation. | When adjusting hashing iteration counts or integrating company SSO/LDAP. |
| [`theme/Color.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Color.kt) | Industrial color palette definitions. | When updating company brand colors, status badge shades, or background tones. |
| [`theme/Theme.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Theme.kt) | Material 3 light/dark color schemes and typography. | When changing typography scales or dark mode behavior. |
| [`ui/components/CommonComponents.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/components/CommonComponents.kt) | Reusable UI widgets: `AppHeader`, `StatusBadge`, `MetricCard`, `QCButton`. | When altering the global appearance of headers, buttons, cards, or badges. |
| [`ui/screens/LoginScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/screens/LoginScreen.kt) | Authentication UI. | When adjusting login layout, adding password reveal toggle, or remember-me features. |
| [`ui/screens/SelectScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/screens/SelectScreen.kt) | Check sheet picker grid with admin builder entry. | When changing check sheet cards, station metadata display, or quick actions. |
| [`ui/screens/DetailsScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/screens/DetailsScreen.kt) | Sequential barcode scanning & manual unit field entry. | When modifying scan step UI, audio beep feedback, or field autofocus behavior. |
| [`ui/screens/ChecksheetScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/screens/ChecksheetScreen.kt) | Test execution matrix, photo capture gate, defect modal, and final submission. | When modifying photo preview dialogs, test button behavior, or defect note dialogs. |
| [`ui/screens/RecordsScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/screens/RecordsScreen.kt) | Historical inspection browser, search filters, and detail viewer. | When adding export buttons (PDF/Excel), date range pickers, or custom filters. |
| [`ui/builder/BuilderScreen.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/ui/builder/BuilderScreen.kt) | 4-tab live check sheet editor, Excel list importer, and barcode sandbox. | When adding new check sheet attributes, validation rules, or rule simulators. |

---

### Practical Change Recipes

#### Recipe 1: Customizing Colors and Industrial Theme
To alter the visual style or match your factory's corporate identity:

1. Open [`android_app/app/src/main/java/com/example/qcsystem/theme/Color.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Color.kt):
   ```kotlin
   // Change the brand primary navy
   val QcPrimary = Color(0xFF1D4E89)     // Replace with your hex code
   val QcPrimaryDark = Color(0xFF163C6B)

   // Change the Pass (OK), Fail (NG), and Rework (RW) badge indicators
   val QcOk = Color(0xFF1B8A4B)          // Manufacturing Pass Green
   val QcNg = Color(0xFFC0392B)          // Manufacturing Defect Red
   val QcRw = Color(0xFFD98200)          // Manufacturing Rework Amber
   ```
2. Open [`android_app/app/src/main/java/com/example/qcsystem/theme/Theme.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/theme/Theme.kt) to configure status bar colors or switch color scheme assignments.

---

#### Recipe 2: Modifying Data Models and Adding Unit Fields
To introduce a new attribute to inspections (e.g., adding `factory_shift` or `station_id`):

1. Open [`android_app/app/src/main/java/com/example/qcsystem/model/Models.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/model/Models.kt):
   ```kotlin
   @Serializable
   data class Inspection(
       val id: Long = 0,
       val checksheetKey: String,
       val checksheetName: String,
       val serialNumber: String,
       val mainBoardNo: String = "",
       val shift: String = "Day",        // <-- Add your new field here
       val unitFields: Map<String, String> = emptyMap(),
       ...
   )
   ```
2. Update [`AppDatabase.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt) as explained in Recipe 3.

---

#### Recipe 3: Updating the SQLite Database Schema & Migrations
When adding a new column to the local SQLite database:

1. Open [`android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt).
2. Increment `DATABASE_VERSION`:
   ```kotlin
   companion object {
       const val DATABASE_NAME = "qc_system.db"
       const val DATABASE_VERSION = 2 // <-- Increment version
   }
   ```
3. Add migration logic in `onUpgrade`:
   ```kotlin
   override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
       if (oldVersion < 2) {
           db.execSQL("ALTER TABLE inspections ADD COLUMN shift TEXT NOT NULL DEFAULT 'Day';")
       }
   }
   ```
4. Update `saveInspection()` and `cursorToInspection()` in `AppDatabase.kt` to write and read the new column.

---

#### Recipe 4: Adding or Modifying Barcode Scanning Rules
The scanning engine supports 6 parsing types (`raw`, `delimited`, `split`, `regex`, `json`, `fixed`). If your factory introduces a custom barcode symbology or encoding format (e.g., XML or Base64):

1. Open [`android_app/app/src/main/java/com/example/qcsystem/scanner/ScanningEngine.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/scanner/ScanningEngine.kt).
2. Locate `parseScan()`:
   ```kotlin
   return when (rule.type) {
       "raw" -> parseRaw(text, rule)
       "delimited" -> parseDelimited(text, rule)
       "split" -> parseSplit(text, rule)
       "regex" -> parseRegex(text, rule)
       "json" -> parseJson(text, rule)
       "fixed" -> parseFixed(text, rule)
       "custom_prefix" -> parseCustomPrefix(text, rule) // <-- Add new handler
       else -> throw ScanParseError("Unknown parse type '${rule.type}'.")
   }
   ```
3. Implement your parsing logic:
   ```kotlin
   private fun parseCustomPrefix(text: String, rule: ScanRule): Map<String, String> {
       // Custom token parsing logic
       val out = mutableMapOf<String, String>()
       ...
       return cleanValues(out, rule)
   }
   ```
4. Add corresponding unit tests in [`ScanningEngineTest.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/test/java/com/example/qcsystem/ScanningEngineTest.kt).

---

#### Recipe 5: Adding a New Screen and Navigation Route
To introduce a new screen (e.g., `SettingsScreen` or `AnalyticsScreen`):

1. **Define the NavKey** in [`NavigationKeys.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/NavigationKeys.kt):
   ```kotlin
   @Serializable
   data object SettingsNavKey : NavKey
   ```
2. **Create the Composable Screen** in `android_app/app/src/main/java/com/example/qcsystem/ui/screens/SettingsScreen.kt`:
   ```kotlin
   @Composable
   fun SettingsScreen(onBack: () -> Unit) {
       Scaffold(
           topBar = { AppHeader(title = "App Settings", onBack = onBack) }
       ) { innerPadding ->
           Column(modifier = Modifier.padding(innerPadding)) {
               Text("Settings content goes here")
           }
       }
   }
   ```
3. **Register the Destination** in [`Navigation.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/Navigation.kt):
   ```kotlin
   when (val currentKey = backstack.lastOrNull()) {
       is SettingsNavKey -> {
           SettingsScreen(
               onBack = { backstack.removeLastOrNull() }
           )
       }
       ...
   }
   ```
4. **Trigger Navigation** from any other screen:
   ```kotlin
   onNavigateToSettings = { backstack.add(SettingsNavKey) }
   ```

---

#### Recipe 6: Modifying Camera Settings & Photo Capture FileProvider
Photo capture uses Android's `FileProvider` to request uncompressed high-resolution images from the system camera without storing thumbnails in memory:

1. **FileProvider Declaration**:
   Defined in [`AndroidManifest.xml`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/AndroidManifest.xml) under authorities `com.example.qcsystem.fileprovider`.
2. **Accessible File Paths**:
   Configured in [`file_paths.xml`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/res/xml/file_paths.xml):
   ```xml
   <paths>
       <external-files-path name="photos" path="photos" />
       <files-path name="internal_photos" path="photos" />
   </paths>
   ```
3. **Image Compression & Resolution**:
   Controlled in [`DataRepository.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/DataRepository.kt) inside `savePhoto()`:
   ```kotlin
   // Adjust JPEG quality (default 90) or max dimensions
   bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
   ```

---

#### Recipe 7: Changing Default Users, Passwords, or Cryptographic Salt
Default users are seeded on the first launch of the SQLite database:

1. Open [`android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/java/com/example/qcsystem/data/AppDatabase.kt).
2. Inside `onCreate()`, modify the seeded values:
   ```kotlin
   // Change initial admin credentials
   val (adminHash, adminSalt) = AuthManager.hashPassword("yourNewAdminPassword123")
   db.execSQL("""
       INSERT OR IGNORE INTO users (username, password_hash, salt, full_name, role, created_at)
       VALUES ('admin', '$adminHash', '$adminSalt', 'System Administrator', 'admin', '$now');
   """)
   ```

---

#### Recipe 8: Updating Version Code, Version Name, or Package Name
To prepare a new app version for distribution:

1. Open [`android_app/app/build.gradle.kts`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/build.gradle.kts).
2. Update the `defaultConfig` block:
   ```kotlin
   defaultConfig {
       applicationId = "com.example.qcsystem" // Change if using a custom company namespace
       minSdk = 24
       targetSdk = 36
       versionCode = 2                        // Increment by 1 for each update
       versionName = "1.1"                    // User-visible semantic version
   }
   ```
3. Re-sync Gradle and assemble the new APK.

---

#### Recipe 9: Running Unit Tests & Verifying Integrity
Before committing code changes, run the automated test suite:

```powershell
cd android_app
cmd /c "gradlew.bat test"
```

Unit tests in [`ScanningEngineTest.kt`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/test/java/com/example/qcsystem/ScanningEngineTest.kt) automatically verify:
- Raw barcode string trimming and normalization.
- Delimited key-value token parsing (`SN:123;MODEL:456`).
- Split index extraction (`0`, `1`, `2`).
- Regular expression capture groups.
- Fixed-slice character substring boundaries.
- PBKDF2 cryptographic password hashing and salt verification.

---

## 💻 Desktop Application: Setup & Execution

The desktop application is built with **Python 3**, **Tkinter**, and **SQLite**. It has zero mandatory external dependencies for core inspection workflows.

### Quick Launch (Zero Setup Required)

1. Unpack the repository into any directory (e.g., `C:\qc_system`).
2. Double-click **`Run QC System.bat`**.
   - The script automatically locates `python.exe` on your system, verifies Tkinter support, and starts the system.
3. **Optional Silent Launch**:
   - Run **`Create Desktop Shortcut.bat`** once. It installs a clean desktop shortcut that launches `Run QC System (no console window).bat` silently in the background.

---

### Optional Camera, Barcode & OCR Requirements

To enable webcam photo capture, camera barcode scanning, or automated Haier-style serial OCR cross-checking:

1. Run **`Install Camera Requirements.bat`** once.
2. The batch installer sets up:
   - `opencv-python`: For live camera preview and frame capture.
   - `Pillow`: For image resizing, thumbnailing, and display.
   - `pyzbar` / `numpy`: Opportunistic barcode decoding.
3. **Standalone Code 39 Decoder**:
   - The desktop system contains a proprietary, self-contained Code 39 pixel-pattern decoder that reads alphanumeric serial barcode patterns directly from video frames without requiring external C++ DLLs or administrator rights.
4. **Hardware Serial Verification (OCR + Barcode)**:
   - For labels containing both printed text and an underlying barcode, the desktop app straightens the label using the barcode's detected angle, crops the text band, and executes Tesseract OCR.
   - A candidate serial is only accepted if **3 consecutive video frames** match between the OCR reading and the decoded barcode.

---

## 🔄 End-to-End Inspection Workflow

Both the Android and Desktop implementations follow this standard industrial workflow:

```
[1. User Authentication]
        │
        ▼
[2. Check Sheet Selection] ── (OQC / AUDIT / IQC / Custom Station)
        │
        ▼
[3. Sequential Barcode Scan]
        ├─ Step 1: Scan Unit QR/Barcode (Fills Serial, Model, Panel, etc.)
        ├─ Step 2: Scan Main Board QR (Fills Main Board No.)
        └─ (Manual Fallback / Edit tag: "scanned" vs "edited by hand")
        │
        ▼
[4. Duplicate Check Safeguard] ── (Warns if Serial was already tested on this Sheet)
        │
        ▼
[5. Interactive Test Matrix]
        ├─ 📷 Photo Gate: Capture mandatory photo for each test item
        ├─ 🔘 Select Status: [OK (Pass)]  [NG (Defect)]  [RW (Rework)]
        └─ 📝 Defect Reason: Modal prompt forces observation note on NG/RW
        │
        ▼
[6. Validation & Submission Gate]
        ├─ Blocks submit if any item lacks a photo or result
        ├─ Copies high-res photos to photos/<SHEET>/<serial>_<timestamp>/
        └─ Saves atomic transaction to SQLite (inspections & test_results)
        │
        ▼
[7. Historical Audit & Record Search]
```

---

## 🔍 Barcode Parsing Engine (6 Modes)

Both implementations share the same parsing engine specification, configured via the **Check Sheet Builder**:

| Mode | Format Example | Configuration Parameters | Extracted Fields |
|---|---|---|---|
| `raw` | `MB-77X-AA19` | `target = "serial_number"` | `serial_number = "MB-77X-AA19"` |
| `delimited` | `SN:LED2026;MDL:55UHD;PNL:P-77` | `separator = ";"`, `pairSeparator = ":"`, `map = {"SN":"serial_number", "MDL":"model"}` | `serial_number = "LED2026"`, `model = "55UHD"` |
| `split` | `LED2026001,55UHD,L-441` | `separator = ","`, `map = {"0":"serial_number", "1":"model", "2":"panel_code"}` | `serial_number = "LED2026001"`, `model = "55UHD"`, `panel_code = "L-441"` |
| `regex` | `LED2026777-65OLED-L99` | `pattern = "^(?P<serial_number>[A-Z0-9]+)-(?P<model>[A-Z0-9]+)-(?P<panel>[A-Z0-9]+)$"` | Extracted from named regex capture groups |
| `json` | `{"sn":"S-1","mdl":"43X"}` | `map = {"sn":"serial_number", "mdl":"model"}` | Extracts JSON object keys into mapped fields |
| `fixed` | `DH20RQ002013C90J0501` | `slices = {"material_code":[1,11], "line":[12,13], "serial_number":[1,20]}` | Exact character slice substring boundaries (1-indexed) |

---

## 🗄️ Database Schema & Data Integrity

Data is stored locally in SQLite (`qc_system.db`). The schema is standardized across platforms:

```sql
-- 1. User Profiles & Permissions
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    full_name     TEXT    NOT NULL DEFAULT '',
    role          TEXT    NOT NULL DEFAULT 'inspector', -- 'admin' or 'inspector'
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL
);

-- 2. Master Inspection Records
CREATE TABLE IF NOT EXISTS inspections (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    checksheet_key   TEXT    NOT NULL,
    checksheet_name  TEXT    NOT NULL,
    serial_number    TEXT    NOT NULL,
    main_board_no    TEXT    NOT NULL DEFAULT '',
    unit_fields_json TEXT    NOT NULL DEFAULT '{}',
    operator_id      INTEGER,
    operator_name    TEXT    NOT NULL DEFAULT '',
    overall_result   TEXT    NOT NULL DEFAULT '',      -- 'OK', 'NG', or 'RW'
    total_tests      INTEGER NOT NULL DEFAULT 0,
    ok_count         INTEGER NOT NULL DEFAULT 0,
    ng_count         INTEGER NOT NULL DEFAULT 0,
    rw_count         INTEGER NOT NULL DEFAULT 0,
    saved_at         TEXT    NOT NULL,
    FOREIGN KEY (operator_id) REFERENCES users (id)
);

-- 3. Individual Test Item Audit
CREATE TABLE IF NOT EXISTS test_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    test_order    INTEGER NOT NULL,
    test_name     TEXT    NOT NULL,
    result        TEXT    NOT NULL,                  -- 'OK', 'NG', or 'RW'
    reason        TEXT    NOT NULL DEFAULT '',       -- Mandatory defect observation on NG/RW
    photo_path    TEXT    NOT NULL DEFAULT '',       -- Relative disk path to JPEG image
    recorded_at   TEXT    NOT NULL,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
);

-- Indices for instant serial searches and relationship joining
CREATE INDEX IF NOT EXISTS idx_insp_serial ON inspections (serial_number);
CREATE INDEX IF NOT EXISTS idx_results_insp ON test_results (inspection_id);
```

---

## 🔐 Security Model

Authentication in both the Desktop and Android applications uses industry-standard cryptographic algorithms:
- **Algorithm**: PBKDF2 with HMAC-SHA256 (`PBKDF2WithHmacSHA256`).
- **Iteration Count**: **200,000 iterations**.
- **Salt**: 16-byte cryptographically secure pseudorandom salt generated per user via `SecureRandom` (Android) and `secrets.token_hex` (Python).
- **Key Length**: 256 bits.
- **Verification**: Constant-time byte-array comparison (`MessageDigest.isEqual` / `hmac.compare_digest`) to prevent timing attacks.

---

## ❓ Troubleshooting & FAQ

### Android App
- **Issue: App fails to install via ADB with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`**
  - *Cause*: A version with a different signing key is already installed on the device.
  - *Fix*: Uninstall the existing app first (`adb uninstall com.example.qcsystem`) and reinstall.
- **Issue: Camera opens but photo fails to save**
  - *Cause*: Missing external storage permissions or unmapped FileProvider path.
  - *Fix*: Verify that [`file_paths.xml`](file:///c:/Users/Muhammad%20Sharjeel/Downloads/qc_system/android_app/app/src/main/res/xml/file_paths.xml) includes `<files-path name="internal_photos" path="photos" />`.
- **Issue: Barcode scan camera preview is black or frozen**
  - *Cause*: Android Camera permission was denied.
  - *Fix*: Go to **Settings → Apps → QC System → Permissions** and grant **Camera** access.

### Desktop App
- **Issue: Double clicking `Run QC System.bat` says Python is not found**
  - *Fix*: Install Python 3.10+ from [python.org](https://www.python.org) and make sure to tick **"Add python.exe to PATH"** during setup.
- **Issue: `import tkinter` fails on Linux or modified Python distributions**
  - *Fix*: On Windows, re-run the Python installer, choose **Modify**, and check **tcl/tk and IDLE**. On Ubuntu/Debian, run `sudo apt install python3-tk`.
- **Issue: Scanned barcode types into the box, but fields remain blank**
  - *Cause*: The scan step rule doesn't match the barcode contents.
  - *Fix*: Open **Check Sheet Builder → Scanning Tab**, paste the actual barcode into the **Try a real code** sandbox, and adjust the parsing mode (e.g., switch from `delimited` to `raw`).

---

## 📄 License & Credits

Built for high-reliability manufacturing quality control. Licensed under the MIT License. Internal enterprise use permitted for all factory lines.
