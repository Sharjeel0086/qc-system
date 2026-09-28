package com.example.qcsystem

import com.example.qcsystem.auth.AuthManager
import com.example.qcsystem.model.ScanRule
import com.example.qcsystem.scanner.ScanningEngine
import org.junit.Assert.*
import org.junit.Test

class ScanningEngineTest {

    @Test
    fun testRawScan() {
        val rule = ScanRule(type = "raw", target = "serial_number", trim = true, upper = true)
        val result = ScanningEngine.parseScan("  dh20rq002013c90j0501  ", rule)
        assertEquals("DH20RQ002013C90J0501", result["serial_number"])
    }

    @Test
    fun testDelimitedScan() {
        val rule = ScanRule(
            type = "delimited",
            separator = ";",
            pairSeparator = ":",
            map = mapOf("SN" to "serial_number", "MODEL" to "model")
        )
        val result = ScanningEngine.parseScan("SN:LED2026001;MODEL:55UHD;PANEL:P-7781", rule)
        assertEquals("LED2026001", result["serial_number"])
        assertEquals("55UHD", result["model"])
    }

    @Test
    fun testSplitScan() {
        val rule = ScanRule(
            type = "split",
            separator = ",",
            map = mapOf("0" to "serial_number", "1" to "part_no", "2" to "lot_no")
        )
        val result = ScanningEngine.parseScan("LED2026001,P-441,LOT-99", rule)
        assertEquals("LED2026001", result["serial_number"])
        assertEquals("P-441", result["part_no"])
        assertEquals("LOT-99", result["lot_no"])
    }

    @Test
    fun testFixedSliceScan() {
        val rule = ScanRule(
            type = "fixed",
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
        val result = ScanningEngine.parseScan("DH20RQ002013C90J0501", rule)
        assertEquals("DH20RQ002013C90J0501", result["serial_number"])
        assertEquals("DH20RQ00201", result["material_code"])
        assertEquals("3C", result["production_line"])
        assertEquals("9", result["year_code"])
        assertEquals("0", result["month_code"])
        assertEquals("J", result["day_code"])
        assertEquals("0501", result["unit_number"])
    }

    @Test
    fun testPasswordHashingAndVerification() {
        val (hash, salt) = AuthManager.hashPassword("admin123")
        assertTrue(AuthManager.verifyPassword("admin123", hash, salt))
        assertFalse(AuthManager.verifyPassword("wrongpass", hash, salt))
    }
}
