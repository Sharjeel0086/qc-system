package com.example.qcsystem.scanner

import android.graphics.Bitmap
import com.example.qcsystem.model.ScanRule
import com.google.zxing.BinaryBitmap
import com.google.zxing.MultiFormatReader
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.common.HybridBinarizer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive

class ScanParseError(message: String) : Exception(message)

object ScanningEngine {

    fun parseScan(payload: String?, rule: ScanRule): Map<String, String> {
        if (payload.isNullOrBlank()) {
            throw ScanParseError("Nothing was scanned.")
        }

        var text = payload
        if (rule.trim) text = text.trim()
        if (rule.upper) text = text.uppercase()
        if (rule.stripPrefix.isNotEmpty() && text.startsWith(rule.stripPrefix)) {
            text = text.removePrefix(rule.stripPrefix)
        }
        if (rule.stripSuffix.isNotEmpty() && text.endsWith(rule.stripSuffix)) {
            text = text.removeSuffix(rule.stripSuffix)
        }

        if (text.isEmpty()) {
            throw ScanParseError("The scanned code was empty after trimming.")
        }

        return when (rule.type) {
            "raw" -> parseRaw(text, rule)
            "delimited" -> parseDelimited(text, rule)
            "split" -> parseSplit(text, rule)
            "regex" -> parseRegex(text, rule)
            "json" -> parseJson(text, rule)
            "fixed" -> parseFixed(text, rule)
            else -> throw ScanParseError("Unknown parse type '${rule.type}'.")
        }
    }

    private fun cleanValues(values: Map<String, String>, rule: ScanRule): Map<String, String> {
        val out = mutableMapOf<String, String>()
        for ((key, rawVal) in values) {
            var v = rawVal.trim()
            if (rule.upper) v = v.uppercase()
            if (v.isNotEmpty()) {
                out[key] = v
            }
        }
        return out
    }

    private fun parseRaw(text: String, rule: ScanRule): Map<String, String> {
        val target = rule.target
        if (target.isBlank()) {
            throw ScanParseError("This scan step has no target field set.")
        }
        var res = text
        if (rule.pattern.isNotEmpty()) {
            val match = Regex(rule.pattern).find(text)
                ?: throw ScanParseError("The scanned code did not match the expected pattern.")
            res = if (match.groupValues.size > 1) match.groupValues[1] else match.value
        }
        return cleanValues(mapOf(target to res), rule)
    }

    private fun parseDelimited(text: String, rule: ScanRule): Map<String, String> {
        val sep = if (rule.separator.isNotEmpty()) rule.separator else ";"
        val pairSep = if (rule.pairSeparator.isNotEmpty()) rule.pairSeparator else ":"
        val mapping = rule.map.mapKeys { it.key.trim().uppercase() }
        if (mapping.isEmpty()) {
            throw ScanParseError("This scan step has no key mapping set.")
        }

        val found = mutableMapOf<String, String>()
        val unknown = mutableListOf<String>()

        for (chunk in text.split(sep)) {
            val trimmed = chunk.trim()
            if (trimmed.isEmpty() || !trimmed.contains(pairSep)) continue
            val parts = trimmed.split(pairSep, limit = 2)
            val key = parts[0].trim().uppercase()
            val value = parts.getOrElse(1) { "" }.trim()
            if (mapping.containsKey(key)) {
                found[mapping[key]!!] = value
            } else {
                unknown.add(key)
            }
        }

        if (found.isEmpty()) {
            val keys = mapping.keys.sorted().joinToString(", ")
            val extra = if (unknown.isNotEmpty()) " Found instead: ${unknown.take(6).joinToString(", ")}." else ""
            throw ScanParseError("No expected keys found in the scanned code. Looking for: $keys.$extra")
        }
        return cleanValues(found, rule)
    }

    private fun parseSplit(text: String, rule: ScanRule): Map<String, String> {
        val sep = if (rule.separator.isNotEmpty()) rule.separator else ","
        val mapping = rule.map
        if (mapping.isEmpty()) {
            throw ScanParseError("This scan step has no position mapping set.")
        }

        val parts = text.split(sep).map { it.trim() }
        val found = mutableMapOf<String, String>()

        for ((posStr, field) in mapping) {
            val index = posStr.toIntOrNull() ?: continue
            if (index in parts.indices) {
                found[field] = parts[index]
            }
        }

        if (found.isEmpty()) {
            throw ScanParseError("The scanned code split into ${parts.size} part(s), which does not match the configured positions.")
        }
        return cleanValues(found, rule)
    }

    private fun parseRegex(text: String, rule: ScanRule): Map<String, String> {
        if (rule.pattern.isBlank()) {
            throw ScanParseError("This scan step has no pattern set.")
        }
        val namedRegex = Regex("\\(\\?P<([a-zA-Z0-9_]+)>([^)]+)\\)")
        val groupNames = namedRegex.findAll(rule.pattern).map { it.groupValues[1] }.toList()

        // Standard java regex doesn't support ?P<name>, convert to normal (?<name>...)
        val standardPattern = rule.pattern.replace("?P<", "?<")
        val regex = try {
            Regex(standardPattern)
        } catch (e: Exception) {
            throw ScanParseError("The pattern is not valid: ${e.message}")
        }

        val match = regex.find(text) ?: throw ScanParseError("The scanned code did not match the expected pattern.")

        val found = mutableMapOf<String, String>()
        for (name in groupNames) {
            try {
                val value = match.groups[name]?.value
                if (!value.isNullOrBlank()) {
                    found[name] = value
                }
            } catch (_: Exception) {}
        }

        if (found.isEmpty()) {
            throw ScanParseError("No matching groups found.")
        }
        return cleanValues(found, rule)
    }

    private fun parseJson(text: String, rule: ScanRule): Map<String, String> {
        val jsonElement = try {
            Json.parseToJsonElement(text)
        } catch (e: Exception) {
            throw ScanParseError("The scanned code is not valid JSON: ${e.message}")
        }

        if (jsonElement !is JsonObject) {
            throw ScanParseError("The scanned JSON is not an object.")
        }

        val found = mutableMapOf<String, String>()
        val mapping = rule.map
        val lowerJson = jsonElement.mapKeys { it.key.lowercase() }

        if (mapping.isNotEmpty()) {
            for ((key, field) in mapping) {
                val value = lowerJson[key.lowercase()]?.jsonPrimitive?.content
                if (!value.isNullOrBlank()) {
                    found[field] = value
                }
            }
        } else {
            for ((key, element) in jsonElement) {
                val value = element.jsonPrimitive.content
                if (value.isNotBlank()) {
                    found[key] = value
                }
            }
        }

        if (found.isEmpty()) {
            throw ScanParseError("None of the mapped keys were present in the scanned JSON.")
        }
        return cleanValues(found, rule)
    }

    private fun parseFixed(text: String, rule: ScanRule): Map<String, String> {
        val slices = rule.slices
        if (slices.isEmpty()) {
            throw ScanParseError("This scan step has no character positions set.")
        }

        val found = mutableMapOf<String, String>()
        for ((field, bounds) in slices) {
            if (bounds.size >= 2) {
                val start = bounds[0]
                val end = bounds[1]
                if (start in 0 until text.length) {
                    val actualEnd = minOf(end, text.length)
                    val piece = text.substring(start, actualEnd)
                    if (piece.isNotBlank()) {
                        found[field] = piece
                    }
                }
            }
        }

        if (found.isEmpty()) {
            throw ScanParseError("The scanned code is only ${text.length} character(s) long, shorter than the positions configured.")
        }
        return cleanValues(found, rule)
    }

    fun describeRule(rule: ScanRule): String {
        return when (rule.type) {
            "raw" -> "whole code into '${rule.target.ifEmpty { "?" }}'"
            "delimited" -> "key/value split by '${rule.separator}' -> ${rule.map.size} field(s)"
            "split" -> "positions split by '${rule.separator}' -> ${rule.map.size} field(s)"
            "regex" -> "pattern with named groups"
            "json" -> "JSON object -> ${rule.map.size} field(s)"
            "fixed" -> "fixed positions -> ${rule.slices.size} field(s)"
            else -> rule.type
        }
    }

    fun mappingToText(map: Map<String, String>): String {
        return map.entries.joinToString("\n") { "${it.key} = ${it.value}" }
    }

    fun textToMapping(text: String): Map<String, String> {
        val out = mutableMapOf<String, String>()
        text.lines().forEach { line ->
            val trimmed = line.trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("#") && trimmed.contains("=")) {
                val parts = trimmed.split("=", limit = 2)
                val k = parts[0].trim()
                val v = parts[1].trim()
                if (k.isNotEmpty() && v.isNotEmpty()) {
                    out[k] = v
                }
            }
        }
        return out
    }

    fun slicesToText(slices: Map<String, List<Int>>): String {
        return slices.entries.mapNotNull { (k, v) ->
            if (v.size >= 2) "$k = ${v[0]}, ${v[1]}" else null
        }.joinToString("\n")
    }

    fun textToSlices(text: String): Map<String, List<Int>> {
        val out = mutableMapOf<String, List<Int>>()
        text.lines().forEach { line ->
            val trimmed = line.trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("#") && trimmed.contains("=")) {
                val parts = trimmed.split("=", limit = 2)
                val field = parts[0].trim()
                val bounds = parts[1].split(",").mapNotNull { it.trim().toIntOrNull() }
                if (field.isNotEmpty() && bounds.size >= 2) {
                    out[field] = listOf(bounds[0], bounds[1])
                }
            }
        }
        return out
    }

    /**
     * Decode QR / Code 39 / Code 128 / EAN barcodes directly from an Android Bitmap.
     * Uses ZXing MultiFormatReader in pure Java, 100% offline.
     */
    fun decodeBarcode(bitmap: Bitmap): String? {
        val width = bitmap.width
        val height = bitmap.height
        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)

        val source = RGBLuminanceSource(width, height, pixels)
        val binaryBitmap = BinaryBitmap(HybridBinarizer(source))
        val reader = MultiFormatReader()

        return try {
            reader.decode(binaryBitmap)?.text
        } catch (_: Exception) {
            // Also try inverted
            try {
                val inverted = BinaryBitmap(HybridBinarizer(source.invert()))
                reader.decode(inverted)?.text
            } catch (_: Exception) {
                null
            }
        }
    }
}
