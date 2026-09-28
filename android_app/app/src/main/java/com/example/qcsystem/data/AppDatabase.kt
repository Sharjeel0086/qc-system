package com.example.qcsystem.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.example.qcsystem.auth.AuthManager
import com.example.qcsystem.model.Inspection
import com.example.qcsystem.model.InspectionWithResults
import com.example.qcsystem.model.TestResultItem
import com.example.qcsystem.model.User
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AppDatabase(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        const val DATABASE_NAME = "qc_system.db"
        const val DATABASE_VERSION = 1
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                salt          TEXT    NOT NULL,
                full_name     TEXT    NOT NULL DEFAULT '',
                role          TEXT    NOT NULL DEFAULT 'inspector',
                active        INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    NOT NULL
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS inspections (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                checksheet_key   TEXT NOT NULL,
                checksheet_name  TEXT NOT NULL,
                serial_number    TEXT NOT NULL,
                main_board_no    TEXT NOT NULL DEFAULT '',
                unit_fields_json TEXT NOT NULL DEFAULT '{}',
                operator_id      INTEGER,
                operator_name    TEXT NOT NULL DEFAULT '',
                overall_result   TEXT NOT NULL DEFAULT '',
                total_tests      INTEGER NOT NULL DEFAULT 0,
                ok_count         INTEGER NOT NULL DEFAULT 0,
                ng_count         INTEGER NOT NULL DEFAULT 0,
                rw_count         INTEGER NOT NULL DEFAULT 0,
                saved_at         TEXT NOT NULL,
                FOREIGN KEY (operator_id) REFERENCES users (id)
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS test_results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL,
                test_order    INTEGER NOT NULL,
                test_name     TEXT    NOT NULL,
                result        TEXT    NOT NULL,
                reason        TEXT    NOT NULL DEFAULT '',
                photo_path    TEXT    NOT NULL DEFAULT '',
                recorded_at   TEXT    NOT NULL,
                FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
            );
        """.trimIndent())

        db.execSQL("CREATE INDEX IF NOT EXISTS idx_insp_serial ON inspections (serial_number);")
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_results_insp ON test_results (inspection_id);")

        // Seed default admin
        val (pwHash, salt) = AuthManager.hashPassword("admin123")
        val now = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
        val cv = ContentValues().apply {
            put("username", "admin")
            put("password_hash", pwHash)
            put("salt", salt)
            put("full_name", "Default Administrator")
            put("role", "admin")
            put("active", 1)
            put("created_at", now)
        }
        db.insert("users", null, cv)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Migration logic if needed in future
    }

    // --- Users ---

    fun getUserByUsername(username: String): User? {
        val db = readableDatabase
        val cursor = db.rawQuery(
            "SELECT * FROM users WHERE username = ? AND active = 1",
            arrayOf(username.trim())
        )
        return cursor.use {
            if (it.moveToFirst()) {
                User(
                    id = it.getLong(it.getColumnIndexOrThrow("id")),
                    username = it.getString(it.getColumnIndexOrThrow("username")),
                    passwordHash = it.getString(it.getColumnIndexOrThrow("password_hash")),
                    salt = it.getString(it.getColumnIndexOrThrow("salt")),
                    fullName = it.getString(it.getColumnIndexOrThrow("full_name")),
                    role = it.getString(it.getColumnIndexOrThrow("role")),
                    active = it.getInt(it.getColumnIndexOrThrow("active")) == 1,
                    createdAt = it.getString(it.getColumnIndexOrThrow("created_at"))
                )
            } else null
        }
    }

    fun createUser(username: String, password: String, fullName: String = "", role: String = "inspector"): Long {
        val (pwHash, salt) = AuthManager.hashPassword(password)
        val now = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
        val cv = ContentValues().apply {
            put("username", username.trim())
            put("password_hash", pwHash)
            put("salt", salt)
            put("full_name", fullName)
            put("role", role)
            put("active", 1)
            put("created_at", now)
        }
        return writableDatabase.insertOrThrow("users", null, cv)
    }

    fun setPassword(username: String, newPassword: String) {
        val (pwHash, salt) = AuthManager.hashPassword(newPassword)
        val cv = ContentValues().apply {
            put("password_hash", pwHash)
            put("salt", salt)
        }
        writableDatabase.update("users", cv, "username = ?", arrayOf(username.trim()))
    }

    // --- Inspections ---

    fun saveInspection(
        checksheetKey: String,
        checksheetName: String,
        unitFields: Map<String, String>,
        results: List<TestResultItem>,
        operatorId: Long?,
        operatorName: String
    ): Pair<Long, String> {
        val now = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
        val okCount = results.count { it.result == "OK" }
        val ngCount = results.count { it.result == "NG" }
        val rwCount = results.count { it.result == "RW" }

        val overall = when {
            ngCount > 0 -> "NG"
            rwCount > 0 -> "RW"
            else -> "OK"
        }

        val serial = unitFields["serial_number"].orEmpty()
        val board = unitFields["main_board_no"].orEmpty()
        val fieldsJson = Json.encodeToString(unitFields)

        val db = writableDatabase
        db.beginTransaction()
        try {
            val cv = ContentValues().apply {
                put("checksheet_key", checksheetKey)
                put("checksheet_name", checksheetName)
                put("serial_number", serial)
                put("main_board_no", board)
                put("unit_fields_json", fieldsJson)
                put("operator_id", operatorId)
                put("operator_name", operatorName)
                put("overall_result", overall)
                put("total_tests", results.size)
                put("ok_count", okCount)
                put("ng_count", ngCount)
                put("rw_count", rwCount)
                put("saved_at", now)
            }
            val inspId = db.insertOrThrow("inspections", null, cv)

            for (r in results) {
                val rCv = ContentValues().apply {
                    put("inspection_id", inspId)
                    put("test_order", r.testOrder)
                    put("test_name", r.testName)
                    put("result", r.result)
                    put("reason", r.reason)
                    put("photo_path", r.photoPath)
                    put("recorded_at", now)
                }
                db.insertOrThrow("test_results", null, rCv)
            }

            db.setTransactionSuccessful()
            return inspId to overall
        } finally {
            db.endTransaction()
        }
    }

    fun listInspections(search: String = "", checksheetKey: String = "", limit: Int = 200): List<Inspection> {
        val db = readableDatabase
        val conditions = mutableListOf<String>()
        val args = mutableListOf<String>()

        if (search.isNotBlank()) {
            conditions.add("(serial_number LIKE ? OR main_board_no LIKE ? OR operator_name LIKE ?)")
            val like = "%${search.trim()}%"
            args.add(like)
            args.add(like)
            args.add(like)
        }

        if (checksheetKey.isNotBlank()) {
            conditions.add("checksheet_key = ?")
            args.add(checksheetKey)
        }

        val where = if (conditions.isNotEmpty()) "WHERE " + conditions.joinToString(" AND ") else ""
        args.add(limit.toString())

        val sql = "SELECT * FROM inspections $where ORDER BY id DESC LIMIT ?"
        val cursor = db.rawQuery(sql, args.toTypedArray())

        val list = mutableListOf<Inspection>()
        cursor.use {
            while (it.moveToNext()) {
                val fieldsJson = it.getString(it.getColumnIndexOrThrow("unit_fields_json"))
                val fieldsMap: Map<String, String> = try {
                    Json.decodeFromString(fieldsJson)
                } catch (_: Exception) {
                    emptyMap()
                }

                list.add(
                    Inspection(
                        id = it.getLong(it.getColumnIndexOrThrow("id")),
                        checksheetKey = it.getString(it.getColumnIndexOrThrow("checksheet_key")),
                        checksheetName = it.getString(it.getColumnIndexOrThrow("checksheet_name")),
                        serialNumber = it.getString(it.getColumnIndexOrThrow("serial_number")),
                        mainBoardNo = it.getString(it.getColumnIndexOrThrow("main_board_no")),
                        unitFields = fieldsMap,
                        operatorId = if (it.isNull(it.getColumnIndexOrThrow("operator_id"))) null else it.getLong(it.getColumnIndexOrThrow("operator_id")),
                        operatorName = it.getString(it.getColumnIndexOrThrow("operator_name")),
                        overallResult = it.getString(it.getColumnIndexOrThrow("overall_result")),
                        totalTests = it.getInt(it.getColumnIndexOrThrow("total_tests")),
                        okCount = it.getInt(it.getColumnIndexOrThrow("ok_count")),
                        ngCount = it.getInt(it.getColumnIndexOrThrow("ng_count")),
                        rwCount = it.getInt(it.getColumnIndexOrThrow("rw_count")),
                        savedAt = it.getString(it.getColumnIndexOrThrow("saved_at"))
                    )
                )
            }
        }
        return list
    }

    fun getInspection(inspId: Long): InspectionWithResults? {
        val db = readableDatabase
        val headCursor = db.rawQuery("SELECT * FROM inspections WHERE id = ?", arrayOf(inspId.toString()))
        val head = headCursor.use {
            if (it.moveToFirst()) {
                val fieldsJson = it.getString(it.getColumnIndexOrThrow("unit_fields_json"))
                val fieldsMap: Map<String, String> = try {
                    Json.decodeFromString(fieldsJson)
                } catch (_: Exception) {
                    emptyMap()
                }
                Inspection(
                    id = it.getLong(it.getColumnIndexOrThrow("id")),
                    checksheetKey = it.getString(it.getColumnIndexOrThrow("checksheet_key")),
                    checksheetName = it.getString(it.getColumnIndexOrThrow("checksheet_name")),
                    serialNumber = it.getString(it.getColumnIndexOrThrow("serial_number")),
                    mainBoardNo = it.getString(it.getColumnIndexOrThrow("main_board_no")),
                    unitFields = fieldsMap,
                    operatorId = if (it.isNull(it.getColumnIndexOrThrow("operator_id"))) null else it.getLong(it.getColumnIndexOrThrow("operator_id")),
                    operatorName = it.getString(it.getColumnIndexOrThrow("operator_name")),
                    overallResult = it.getString(it.getColumnIndexOrThrow("overall_result")),
                    totalTests = it.getInt(it.getColumnIndexOrThrow("total_tests")),
                    okCount = it.getInt(it.getColumnIndexOrThrow("ok_count")),
                    ngCount = it.getInt(it.getColumnIndexOrThrow("ng_count")),
                    rwCount = it.getInt(it.getColumnIndexOrThrow("rw_count")),
                    savedAt = it.getString(it.getColumnIndexOrThrow("saved_at"))
                )
            } else null
        } ?: return null

        val resultsCursor = db.rawQuery("SELECT * FROM test_results WHERE inspection_id = ? ORDER BY test_order", arrayOf(inspId.toString()))
        val results = mutableListOf<TestResultItem>()
        resultsCursor.use {
            while (it.moveToNext()) {
                results.add(
                    TestResultItem(
                        id = it.getLong(it.getColumnIndexOrThrow("id")),
                        inspectionId = it.getLong(it.getColumnIndexOrThrow("inspection_id")),
                        testOrder = it.getInt(it.getColumnIndexOrThrow("test_order")),
                        testName = it.getString(it.getColumnIndexOrThrow("test_name")),
                        result = it.getString(it.getColumnIndexOrThrow("result")),
                        reason = it.getString(it.getColumnIndexOrThrow("reason")),
                        photoPath = it.getString(it.getColumnIndexOrThrow("photo_path")),
                        recordedAt = it.getString(it.getColumnIndexOrThrow("recorded_at"))
                    )
                )
            }
        }

        return InspectionWithResults(head, results)
    }

    fun findDuplicate(checksheetKey: String, serialNumber: String): Inspection? {
        val db = readableDatabase
        val cursor = db.rawQuery(
            "SELECT * FROM inspections WHERE checksheet_key = ? AND serial_number = ? ORDER BY id DESC LIMIT 1",
            arrayOf(checksheetKey, serialNumber.trim())
        )
        return cursor.use {
            if (it.moveToFirst()) {
                Inspection(
                    id = it.getLong(it.getColumnIndexOrThrow("id")),
                    checksheetKey = it.getString(it.getColumnIndexOrThrow("checksheet_key")),
                    checksheetName = it.getString(it.getColumnIndexOrThrow("checksheet_name")),
                    serialNumber = it.getString(it.getColumnIndexOrThrow("serial_number")),
                    mainBoardNo = it.getString(it.getColumnIndexOrThrow("main_board_no")),
                    operatorName = it.getString(it.getColumnIndexOrThrow("operator_name")),
                    overallResult = it.getString(it.getColumnIndexOrThrow("overall_result")),
                    savedAt = it.getString(it.getColumnIndexOrThrow("saved_at"))
                )
            } else null
        }
    }
}
