package com.example.qcsystem.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.example.qcsystem.model.Checksheet
import com.example.qcsystem.model.Inspection
import com.example.qcsystem.model.InspectionWithResults
import com.example.qcsystem.model.ScanRule
import com.example.qcsystem.model.ScanTarget
import com.example.qcsystem.model.TestResultItem
import com.example.qcsystem.model.UnitField
import com.example.qcsystem.model.User
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DataRepository(private val context: Context) {

    private val db = AppDatabase(context)
    private val json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
        encodeDefaults = true
    }

    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: StateFlow<User?> = _currentUser

    private val _checksheets = MutableStateFlow<Map<String, Checksheet>>(emptyMap())
    val checksheets: StateFlow<Map<String, Checksheet>> = _checksheets

    private val checksheetsFile = File(context.filesDir, "checksheets.json")
    private val backupDir = File(context.filesDir, "backups").apply { mkdirs() }
    private val photoRoot = File(context.filesDir, "photos").apply { mkdirs() }

    init {
        loadChecksheets()
    }

    fun setCurrentUser(user: User?) {
        _currentUser.value = user
    }

    // --- Checksheets Management ---

    fun loadChecksheets() {
        if (!checksheetsFile.exists()) {
            val defaults = getDefaultChecksheets()
            saveChecksheets(defaults, createBackup = false)
            _checksheets.value = defaults
        } else {
            try {
                val content = checksheetsFile.readText()
                val map: Map<String, Checksheet> = json.decodeFromString(content)
                _checksheets.value = map
            } catch (e: Exception) {
                val defaults = getDefaultChecksheets()
                _checksheets.value = defaults
            }
        }
    }

    fun saveChecksheets(sheets: Map<String, Checksheet>, createBackup: Boolean = true) {
        if (createBackup && checksheetsFile.exists()) {
            val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val backupFile = File(backupDir, "checksheets_$stamp.json")
            checksheetsFile.copyTo(backupFile, overwrite = true)
            trimBackups()
        }

        val content = json.encodeToString(sheets)
        checksheetsFile.writeText(content)
        _checksheets.value = sheets
    }

    private fun trimBackups(keep: Int = 20) {
        val files = backupDir.listFiles()?.sortedBy { it.name } ?: return
        if (files.size > keep) {
            for (f in files.take(files.size - keep)) {
                f.delete()
            }
        }
    }

    // --- Inspections ---

    suspend fun saveInspection(
        checksheetKey: String,
        checksheetName: String,
        unitFields: Map<String, String>,
        results: List<TestResultItem>,
        photoUriMap: Map<Int, Uri?>
    ): Pair<Long, String> = withContext(Dispatchers.IO) {
        val user = _currentUser.value
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val serial = unitFields["serial_number"] ?: "unit"
        val safeSerial = serial.filter { it.isLetterOrDigit() || it == '-' || it == '_' }.ifEmpty { "unit" }
        val targetFolder = File(photoRoot, "$checksheetKey/${safeSerial}_$stamp").apply { mkdirs() }

        val processedResults = results.mapIndexed { index, row ->
            val uri = photoUriMap[index]
            var storedPath = row.photoPath
            if (uri != null) {
                val safeTest = row.testName.map { if (it.isLetterOrDigit()) it else '_' }.joinToString("").take(40)
                val destFile = File(targetFolder, String.format(Locale.US, "%02d_%s.jpg", index + 1, safeTest))
                try {
                    context.contentResolver.openInputStream(uri)?.use { input ->
                        FileOutputStream(destFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                    storedPath = destFile.absolutePath
                } catch (e: Exception) {
                    storedPath = uri.toString()
                }
            }
            row.copy(photoPath = storedPath)
        }

        db.saveInspection(
            checksheetKey = checksheetKey,
            checksheetName = checksheetName,
            unitFields = unitFields,
            results = processedResults,
            operatorId = user?.id,
            operatorName = user?.fullName?.ifBlank { user.username } ?: "Inspector"
        )
    }

    fun listInspections(search: String = "", sheetKey: String = ""): List<Inspection> {
        return db.listInspections(search, sheetKey)
    }

    fun getInspection(id: Long): InspectionWithResults? {
        return db.getInspection(id)
    }

    fun findDuplicate(checksheetKey: String, serialNumber: String): Inspection? {
        return db.findDuplicate(checksheetKey, serialNumber)
    }

    // --- Users ---

    fun getUserByUsername(username: String): User? = db.getUserByUsername(username)
    fun createUser(username: String, pass: String, fullName: String, role: String) = db.createUser(username, pass, fullName, role)
    fun setPassword(username: String, newPass: String) = db.setPassword(username, newPass)

    // --- Default Checksheets from data/checksheets.json ---
    private fun getDefaultChecksheets(): Map<String, Checksheet> {
        return mapOf(
            "OQC" to Checksheet(
                key = "OQC",
                name = "OQC Check Sheet",
                subtitle = "Outgoing quality control - finished LED unit",
                unitFields = listOf(
                    UnitField("serial_number", "Serial number", required = true),
                    UnitField("main_board_no", "Main board number", required = true),
                    UnitField("model", "Model / size", required = true),
                    UnitField("panel_no", "Panel number", required = false),
                    UnitField("power_board_no", "Power board number", required = false),
                    UnitField("production_line", "Production line (serial pos 12-13)", required = false),
                    UnitField("lot_no", "Lot / batch number", required = false),
                    UnitField("remarks", "Remarks", required = false),
                    UnitField("material_code", "Material code (serial pos 1-11)", required = false),
                    UnitField("year_code", "Year of manufacture (serial pos 14)", required = false),
                    UnitField("month_code", "Month of manufacture (serial pos 15)", required = false),
                    UnitField("day_code", "Day of manufacture (serial pos 16)", required = false),
                    UnitField("unit_number", "Unit number (serial pos 17-20)", required = false)
                ),
                scanTargets = listOf(
                    ScanTarget(
                        id = "unit_qr",
                        label = "Unit QR / Barcode",
                        prompt = "Scan the unit serial barcode or QR code",
                        rule = ScanRule(
                            type = "fixed",
                            trim = true,
                            upper = true,
                            slices = mapOf(
                                "serial_number" to listOf(0, 20),
                                "material_code" to listOf(0, 11),
                                "production_line" to listOf(11, 13),
                                "year_code" to listOf(13, 14),
                                "month_code" to listOf(14, 15),
                                "day_code" to listOf(15, 16),
                                "unit_number" to listOf(16, 20)
                            )
                        )
                    ),
                    ScanTarget(
                        id = "board_qr",
                        label = "Main board QR code",
                        prompt = "Scan the QR code printed on the main board",
                        rule = ScanRule(
                            type = "raw",
                            target = "main_board_no",
                            trim = true,
                            upper = true
                        )
                    )
                ),
                tests = listOf(
                    "Appearance - cabinet and bezel",
                    "Appearance - screen surface and scratches",
                    "Label and barcode check",
                    "Accessories and packing list",
                    "Power on / boot time",
                    "Display uniformity - white screen",
                    "Display uniformity - black screen",
                    "Dead pixel / bright dot check",
                    "Colour bar pattern test",
                    "Backlight leakage test",
                    "Audio output - left and right",
                    "Remote control function test",
                    "HDMI input test",
                    "USB port and media playback",
                    "Menu and OSD function",
                    "Stand / wall mount fitting",
                    "High voltage / earth continuity test",
                    "Final packing condition"
                )
            ),
            "AUDIT" to Checksheet(
                key = "AUDIT",
                name = "Audit Check Sheet",
                subtitle = "Line audit sampling",
                unitFields = listOf(
                    UnitField("serial_number", "Serial number", required = true),
                    UnitField("main_board_no", "Main board number", required = true),
                    UnitField("model", "Model / size", required = true),
                    UnitField("audit_stage", "Audit stage", required = false),
                    UnitField("shift", "Shift", required = false),
                    UnitField("remarks", "Remarks", required = false)
                ),
                scanTargets = listOf(
                    ScanTarget(
                        id = "unit_qr",
                        label = "Unit QR code",
                        prompt = "Scan the unit QR code",
                        rule = ScanRule(
                            type = "delimited",
                            separator = ";",
                            pairSeparator = ":",
                            trim = true,
                            map = mapOf(
                                "SN" to "serial_number",
                                "MODEL" to "model"
                            )
                        )
                    ),
                    ScanTarget(
                        id = "board_qr",
                        label = "Main board QR code",
                        prompt = "Scan the main board QR code",
                        rule = ScanRule(
                            type = "raw",
                            target = "main_board_no",
                            upper = true
                        )
                    )
                ),
                tests = listOf(
                    "Workmanship and assembly check",
                    "Screw torque and fitting",
                    "Cable routing and connector seating",
                    "Sticker position and printing quality",
                    "Carton and printing check",
                    "Function test - full cycle",
                    "Ageing test result verification",
                    "Safety test record verification"
                )
            ),
            "IQC" to Checksheet(
                key = "IQC",
                name = "IQC Check Sheet",
                subtitle = "Incoming material inspection",
                unitFields = listOf(
                    UnitField("serial_number", "Serial / reference number", required = true),
                    UnitField("main_board_no", "Main board number", required = true),
                    UnitField("supplier", "Supplier", required = true),
                    UnitField("part_no", "Part number", required = false),
                    UnitField("lot_no", "Lot / batch number", required = false),
                    UnitField("remarks", "Remarks", required = false)
                ),
                scanTargets = listOf(
                    ScanTarget(
                        id = "carton_barcode",
                        label = "Carton barcode",
                        prompt = "Scan the barcode on the incoming carton",
                        rule = ScanRule(
                            type = "split",
                            separator = ",",
                            trim = true,
                            map = mapOf(
                                "0" to "serial_number",
                                "1" to "part_no",
                                "2" to "lot_no"
                            )
                        )
                    ),
                    ScanTarget(
                        id = "board_qr",
                        label = "Main board QR code",
                        prompt = "Scan the main board QR code",
                        rule = ScanRule(
                            type = "raw",
                            target = "main_board_no",
                            upper = true
                        )
                    )
                ),
                tests = listOf(
                    "Packing condition on arrival",
                    "Quantity verification",
                    "Part marking and label check",
                    "Visual defect check",
                    "Dimension check",
                    "Electrical function sample test"
                )
            )
        )
    }
}
