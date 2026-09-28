package com.example.qcsystem

import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Serializable
data object LoginNavKey : NavKey

@Serializable
data object SelectNavKey : NavKey

@Serializable
data class DetailsNavKey(val checksheetKey: String) : NavKey

@Serializable
data class ChecksheetNavKey(
    val checksheetKey: String,
    val unitFields: Map<String, String>
) : NavKey

@Serializable
data object RecordsNavKey : NavKey

@Serializable
data class RecordDetailNavKey(val inspectionId: Long) : NavKey

@Serializable
data class BuilderNavKey(val sheetKey: String? = null) : NavKey
