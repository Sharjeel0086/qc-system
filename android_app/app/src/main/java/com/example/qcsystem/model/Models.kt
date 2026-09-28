package com.example.qcsystem.model

import kotlinx.serialization.Serializable

@Serializable
data class User(
    val id: Long = 0,
    val username: String,
    val passwordHash: String,
    val salt: String,
    val fullName: String = "",
    val role: String = "inspector", // "admin" or "inspector"
    val active: Boolean = true,
    val createdAt: String = ""
)

@Serializable
data class UnitField(
    val id: String,
    val label: String,
    val required: Boolean = false
) {
    val isMandatory: Boolean
        get() = id == "serial_number" || id == "main_board_no"
}

@Serializable
data class ScanRule(
    val type: String = "raw", // "raw", "delimited", "split", "regex", "json", "fixed"
    val target: String = "",
    val separator: String = ";",
    val pairSeparator: String = ":",
    val map: Map<String, String> = emptyMap(),
    val pattern: String = "",
    val slices: Map<String, List<Int>> = emptyMap(),
    val trim: Boolean = true,
    val upper: Boolean = true,
    val stripPrefix: String = "",
    val stripSuffix: String = ""
)

@Serializable
data class ScanTarget(
    val id: String = "scan",
    val label: String = "Scan code",
    val prompt: String = "Scan the code",
    val rule: ScanRule = ScanRule()
) {
    val targetFields: List<String>
        get() {
            return when (rule.type) {
                "raw" -> if (rule.target.isNotBlank()) listOf(rule.target) else emptyList()
                "delimited", "split", "json" -> rule.map.values.toList()
                "fixed" -> rule.slices.keys.toList()
                "regex" -> {
                    // Try to extract named capture groups or simple regex
                    val regex = Regex("\\(\\?P<([a-zA-Z0-9_]+)>")
                    regex.findAll(rule.pattern).map { it.groupValues[1] }.toList()
                }
                else -> emptyList()
            }
        }
}

@Serializable
data class Checksheet(
    val key: String,
    val name: String,
    val subtitle: String = "",
    val unitFields: List<UnitField> = emptyList(),
    val scanTargets: List<ScanTarget> = emptyList(),
    val tests: List<String> = emptyList()
) {
    val testCount: Int get() = tests.size

    fun fieldLabel(fieldId: String): String {
        return unitFields.find { it.id == fieldId }?.label ?: fieldId
    }

    fun scannableFields(): Set<String> {
        return scanTargets.flatMap { it.targetFields }.toSet()
    }
}

@Serializable
data class Inspection(
    val id: Long = 0,
    val checksheetKey: String,
    val checksheetName: String,
    val serialNumber: String,
    val mainBoardNo: String = "",
    val unitFields: Map<String, String> = emptyMap(),
    val operatorId: Long? = null,
    val operatorName: String = "",
    val overallResult: String = "", // "OK", "NG", "RW"
    val totalTests: Int = 0,
    val okCount: Int = 0,
    val ngCount: Int = 0,
    val rwCount: Int = 0,
    val savedAt: String = ""
)

@Serializable
data class TestResultItem(
    val id: Long = 0,
    val inspectionId: Long = 0,
    val testOrder: Int,
    val testName: String,
    val result: String, // "OK", "NG", "RW"
    val reason: String = "",
    val photoPath: String = "",
    val recordedAt: String = ""
)

data class InspectionWithResults(
    val inspection: Inspection,
    val results: List<TestResultItem>
)
