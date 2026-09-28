package com.example.qcsystem.ui.screens

import android.graphics.Bitmap
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.model.Checksheet
import com.example.qcsystem.model.Inspection
import com.example.qcsystem.scanner.ScanningEngine
import com.example.qcsystem.scanner.ScanParseError
import com.example.qcsystem.theme.*
import com.example.qcsystem.ui.components.QcHeaderBar

@Composable
fun DetailsScreen(
    repository: DataRepository,
    checksheetKey: String,
    onBack: () -> Unit,
    onContinue: (Map<String, String>) -> Unit
) {
    val context = LocalContext.current
    val checksheets by repository.checksheets.collectAsState()
    val sheet = checksheets[checksheetKey] ?: return

    val steps = sheet.scanTargets
    var stepIndex by remember { mutableIntStateOf(0) }
    val doneSteps = remember { mutableStateListOf<Int>() }

    var scanInput by remember { mutableStateOf("") }
    var scanStatusMessage by remember { mutableStateOf("") }
    var scanStatusColor by remember { mutableStateOf(QcMuted) }

    val fieldValues = remember {
        mutableStateMapOf<String, String>().apply {
            sheet.unitFields.forEach { put(it.id, "") }
        }
    }

    val scannedFieldIds = remember { mutableStateListOf<String>() }
    val editedByHandIds = remember { mutableStateListOf<String>() }

    var duplicateWarningInspection by remember { mutableStateOf<Inspection?>(null) }
    var validationError by remember { mutableStateOf("") }

    // Camera scanner launcher (uses built-in ZXing decoder on the captured snapshot!)
    val cameraScannerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { bitmap: Bitmap? ->
        if (bitmap != null) {
            val decoded = ScanningEngine.decodeBarcode(bitmap)
            if (!decoded.isNullOrBlank()) {
                scanInput = decoded
                // Trigger parse immediately
                if (stepIndex < steps.size) {
                    val step = steps[stepIndex]
                    try {
                        val parsed = ScanningEngine.parseScan(decoded, step.rule)
                        val applied = mutableListOf<String>()
                        for ((fid, v) in parsed) {
                            if (fieldValues.containsKey(fid)) {
                                fieldValues[fid] = v
                                if (!scannedFieldIds.contains(fid)) scannedFieldIds.add(fid)
                                editedByHandIds.remove(fid)
                                applied.add(sheet.fieldLabel(fid))
                            }
                        }
                        if (applied.isNotEmpty()) {
                            scanStatusMessage = "${step.label} read - filled: ${applied.joinToString(", ")}."
                            scanStatusColor = QcOk
                            doneSteps.add(stepIndex)
                            scanInput = ""
                            stepIndex++
                        } else {
                            scanStatusMessage = "Code read, but no matching fields found on this sheet."
                            scanStatusColor = QcRw
                        }
                    } catch (e: ScanParseError) {
                        scanStatusMessage = "Could not parse code: ${e.message}"
                        scanStatusColor = QcNg
                    }
                }
            } else {
                Toast.makeText(context, "No barcode/QR detected. Hold camera closer and steady.", Toast.LENGTH_LONG).show()
            }
        }
    }

    fun submitScan() {
        if (scanInput.isBlank() || stepIndex >= steps.size) return
        val step = steps[stepIndex]
        try {
            val parsed = ScanningEngine.parseScan(scanInput, step.rule)
            val applied = mutableListOf<String>()
            for ((fid, v) in parsed) {
                if (fieldValues.containsKey(fid)) {
                    fieldValues[fid] = v
                    if (!scannedFieldIds.contains(fid)) scannedFieldIds.add(fid)
                    editedByHandIds.remove(fid)
                    applied.add(sheet.fieldLabel(fid))
                }
            }
            if (applied.isNotEmpty()) {
                scanStatusMessage = "${step.label} read - filled: ${applied.joinToString(", ")}."
                scanStatusColor = QcOk
                doneSteps.add(stepIndex)
                scanInput = ""
                stepIndex++
            } else {
                scanStatusMessage = "Code read, but no matching fields found on this sheet."
                scanStatusColor = QcRw
            }
        } catch (e: ScanParseError) {
            scanStatusMessage = "Could not parse code: ${e.message}"
            scanStatusColor = QcNg
        }
    }

    fun proceedToTests() {
        validationError = ""
        val values = fieldValues.toMap()

        // Required field validation
        val missing = sheet.unitFields.filter { it.required && values[it.id].isNullOrBlank() }
        if (missing.isNotEmpty()) {
            validationError = "Scan or type these before continuing: ${missing.joinToString(", ") { it.label }}"
            return
        }

        val serial = values["serial_number"].orEmpty()
        val duplicate = repository.findDuplicate(sheet.key, serial)
        if (duplicate != null) {
            duplicateWarningInspection = duplicate
        } else {
            onContinue(values)
        }
    }

    Scaffold(
        topBar = {
            QcHeaderBar(
                title = sheet.name,
                subtitle = "${sheet.key} - unit details",
                onBack = onBack
            )
        },
        bottomBar = {
            Surface(
                color = QcSurface,
                shadowElevation = 6.dp,
                modifier = Modifier.border(1.dp, QcBorder)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                ) {
                    if (validationError.isNotEmpty()) {
                        Text(
                            text = validationError,
                            color = QcNg,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(bottom = 6.dp)
                        )
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedButton(
                            onClick = onBack,
                            shape = RoundedCornerShape(6.dp)
                        ) {
                            Text("Cancel", color = QcInk)
                        }

                        Button(
                            onClick = { proceedToTests() },
                            colors = ButtonDefaults.buttonColors(containerColor = QcPrimary),
                            shape = RoundedCornerShape(6.dp)
                        ) {
                            Text("Continue to tests", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        },
        containerColor = QcBackground
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Scanner Panel
            if (steps.isNotEmpty()) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(2.dp, QcPrimary, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = QcSurface),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            val stepHeader = if (stepIndex < steps.size) {
                                "STEP ${stepIndex + 1} OF ${steps.size} - ${steps[stepIndex].label.uppercase()}"
                            } else {
                                "SCANNING COMPLETE"
                            }
                            Text(
                                text = stepHeader,
                                color = QcPrimary,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "${doneSteps.size} of ${steps.size} code(s) read",
                                color = QcMuted,
                                fontSize = 12.sp
                            )
                        }

                        val promptText = if (stepIndex < steps.size) steps[stepIndex].prompt else "All codes read"
                        Text(
                            text = promptText,
                            color = QcInk,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(vertical = 8.dp)
                        )

                        if (stepIndex < steps.size) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = scanInput,
                                    onValueChange = { scanInput = it },
                                    modifier = Modifier.weight(1f),
                                    placeholder = { Text("Scan or enter code...") },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                                    keyboardActions = KeyboardActions(onDone = { submitScan() })
                                )

                                Spacer(modifier = Modifier.width(8.dp))

                                Button(
                                    onClick = { submitScan() },
                                    shape = RoundedCornerShape(6.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                                ) {
                                    Text("Read")
                                }
                            }

                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 10.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedButton(
                                    onClick = { cameraScannerLauncher.launch(null) },
                                    shape = RoundedCornerShape(6.dp),
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Scan with camera", fontSize = 12.sp)
                                }

                                TextButton(
                                    onClick = {
                                        if (stepIndex < steps.size) {
                                            scanStatusMessage = "${steps[stepIndex].label} skipped - enter details by hand."
                                            scanStatusColor = QcRw
                                            stepIndex++
                                        }
                                    }
                                ) {
                                    Text("Skip this step", fontSize = 12.sp, color = QcPrimary)
                                }

                                TextButton(
                                    onClick = {
                                        stepIndex = 0
                                        doneSteps.clear()
                                        scannedFieldIds.clear()
                                        editedByHandIds.clear()
                                        scanInput = ""
                                        scanStatusMessage = "Scanning reset. Ready for first code."
                                        scanStatusColor = QcMuted
                                    }
                                ) {
                                    Text("Start over", fontSize = 12.sp, color = QcPrimary)
                                }
                            }
                        }

                        if (scanStatusMessage.isNotEmpty()) {
                            Text(
                                text = scanStatusMessage,
                                color = scanStatusColor,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(top = 8.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
            }

            // Unit details fields
            Text(
                text = "Unit details",
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = QcInk
            )
            Text(
                text = "Scanned values appear below and can still be edited by hand. * required",
                fontSize = 12.sp,
                color = QcMuted,
                modifier = Modifier.padding(bottom = 12.dp)
            )

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, QcBorder, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = QcSurface),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    val scannableSet = sheet.scannableFields()

                    for (field in sheet.unitFields) {
                        val fid = field.id
                        val currentVal = fieldValues[fid] ?: ""

                        Column {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = field.label + if (field.required) " *" else "",
                                        fontWeight = FontWeight.Medium,
                                        fontSize = 13.sp,
                                        color = QcInk
                                    )
                                }

                                val (tagText, tagColor) = when {
                                    editedByHandIds.contains(fid) -> "edited by hand" to QcRw
                                    scannedFieldIds.contains(fid) -> "scanned" to QcOk
                                    scannableSet.contains(fid) -> "scannable" to QcMuted
                                    else -> "" to Color.Transparent
                                }

                                if (tagText.isNotEmpty()) {
                                    Text(
                                        text = tagText,
                                        fontSize = 10.sp,
                                        color = tagColor,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            OutlinedTextField(
                                value = currentVal,
                                onValueChange = { newVal ->
                                    fieldValues[fid] = newVal
                                    if (scannedFieldIds.contains(fid)) {
                                        scannedFieldIds.remove(fid)
                                        if (!editedByHandIds.contains(fid)) editedByHandIds.add(fid)
                                    }
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 4.dp),
                                singleLine = true
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }

    // Duplicate Serial Alert Dialog
    if (duplicateWarningInspection != null) {
        val dup = duplicateWarningInspection!!
        AlertDialog(
            onDismissRequest = { duplicateWarningInspection = null },
            title = { Text("Unit already inspected") },
            text = {
                Text(
                    "Serial ${fieldValues["serial_number"]} was already run on ${sheet.name}.\n\n" +
                    "Saved: ${dup.savedAt.replace("T", "  ")}\n" +
                    "Result: ${dup.overallResult}\n" +
                    "By: ${dup.operatorName}\n\n" +
                    "Start a new inspection for the same unit?"
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        duplicateWarningInspection = null
                        onContinue(fieldValues.toMap())
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Continue anyway")
                }
            },
            dismissButton = {
                TextButton(onClick = { duplicateWarningInspection = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}
