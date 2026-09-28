package com.example.qcsystem.ui.screens

import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.core.content.FileProvider
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.model.Checksheet
import com.example.qcsystem.model.TestResultItem
import com.example.qcsystem.theme.*
import com.example.qcsystem.ui.components.QcHeaderBar
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun ChecksheetScreen(
    repository: DataRepository,
    checksheetKey: String,
    unitFields: Map<String, String>,
    onFinished: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val checksheets by repository.checksheets.collectAsState()
    val sheet = checksheets[checksheetKey] ?: return

    val serial = unitFields["serial_number"].orEmpty()
    val board = unitFields["main_board_no"].orEmpty()

    // Row states
    val photoUris = remember { mutableStateMapOf<Int, Uri?>() }
    val photoNames = remember { mutableStateMapOf<Int, String>() }
    val rowResults = remember { mutableStateMapOf<Int, String>() }
    val rowReasons = remember { mutableStateMapOf<Int, String>() }

    var currentRowIndexForPhoto by remember { mutableIntStateOf(-1) }
    var tempCameraUri by remember { mutableStateOf<Uri?>(null) }
    var previewPhotoUri by remember { mutableStateOf<Uri?>(null) }

    var showExitConfirm by remember { mutableStateOf(false) }
    var saveIncompleteError by remember { mutableStateOf<List<String>?>(null) }
    var isSaving by remember { mutableStateOf(false) }

    // Camera launcher with FileProvider URI for high quality photo capture
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && tempCameraUri != null && currentRowIndexForPhoto >= 0) {
            photoUris[currentRowIndexForPhoto] = tempCameraUri
            photoNames[currentRowIndexForPhoto] = "Captured just now"
        }
    }

    // Gallery picker launcher
    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null && currentRowIndexForPhoto >= 0) {
            photoUris[currentRowIndexForPhoto] = uri
            photoNames[currentRowIndexForPhoto] = "Photo attached"
        }
    }

    fun launchCamera(rowIndex: Int) {
        currentRowIndexForPhoto = rowIndex
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val photoDir = File(context.cacheDir, "photos").apply { mkdirs() }
        val tempFile = File(photoDir, "qc_capture_${rowIndex}_$stamp.jpg")
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", tempFile)
        tempCameraUri = uri
        cameraLauncher.launch(uri)
    }

    fun launchGallery(rowIndex: Int) {
        currentRowIndexForPhoto = rowIndex
        galleryLauncher.launch("image/*")
    }

    fun attemptSave() {
        val incomplete = mutableListOf<String>()
        sheet.tests.forEachIndexed { index, testName ->
            val hasPhoto = photoUris[index] != null
            val result = rowResults[index].orEmpty()
            val reason = rowReasons[index].orEmpty()

            when {
                !hasPhoto -> incomplete.add("${index + 1}. $testName - photo missing")
                result.isEmpty() -> incomplete.add("${index + 1}. $testName - result not selected")
                (result == "NG" || result == "RW") && reason.isBlank() -> {
                    val why = if (result == "NG") "NG reason not filled" else "rework defect not filled"
                    incomplete.add("${index + 1}. $testName - $why")
                }
            }
        }

        if (incomplete.isNotEmpty()) {
            saveIncompleteError = incomplete
            return
        }

        isSaving = true
        coroutineScope.launch {
            val results = sheet.tests.mapIndexed { index, testName ->
                TestResultItem(
                    testOrder = index + 1,
                    testName = testName,
                    result = rowResults[index].orEmpty(),
                    reason = rowReasons[index].orEmpty(),
                    photoPath = ""
                )
            }

            try {
                val (inspId, overall) = repository.saveInspection(
                    checksheetKey = sheet.key,
                    checksheetName = sheet.name,
                    unitFields = unitFields,
                    results = results,
                    photoUriMap = photoUris
                )

                Toast.makeText(context, "Record #$inspId saved. Overall: $overall", Toast.LENGTH_LONG).show()
                onFinished()
            } catch (e: Exception) {
                Toast.makeText(context, "Could not save inspection: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isSaving = false
            }
        }
    }

    val completedCount = remember(photoUris.size, rowResults.size, rowReasons.size) {
        sheet.tests.indices.count { index ->
            val hasPhoto = photoUris[index] != null
            val res = rowResults[index].orEmpty()
            val reason = rowReasons[index].orEmpty()
            hasPhoto && res.isNotEmpty() && (res == "OK" || reason.isNotBlank())
        }
    }

    Scaffold(
        topBar = {
            QcHeaderBar(
                title = sheet.name,
                subtitle = "Serial $serial   |   Main board $board",
                onBack = {
                    val hasEntries = photoUris.isNotEmpty() || rowResults.isNotEmpty()
                    if (hasEntries) {
                        showExitConfirm = true
                    } else {
                        onFinished()
                    }
                }
            )
        },
        bottomBar = {
            Surface(
                color = QcSurface,
                shadowElevation = 6.dp,
                modifier = Modifier.border(1.dp, QcBorder)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "$completedCount of ${sheet.testCount} tests complete",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (completedCount == sheet.testCount) QcOk else QcInk
                        )
                        Text(
                            text = if (completedCount == sheet.testCount) "Ready to save" else "${sheet.testCount - completedCount} incomplete",
                            fontSize = 11.sp,
                            color = QcMuted
                        )
                    }

                    Button(
                        onClick = { attemptSave() },
                        enabled = !isSaving,
                        colors = ButtonDefaults.buttonColors(containerColor = QcPrimary),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        if (isSaving) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White, strokeWidth = 2.dp)
                        } else {
                            Text("Save inspection", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        },
        containerColor = QcBackground
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Text(
                    text = "Test results",
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = QcInk
                )
                Text(
                    text = "Attach a photo after each test, then set the result. NG and RW require a written reason.",
                    fontSize = 12.sp,
                    color = QcMuted,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
            }

            itemsIndexed(sheet.tests) { index, testName ->
                val hasPhoto = photoUris[index] != null
                val photoName = photoNames[index] ?: "required"
                val currentResult = rowResults[index].orEmpty()
                val currentReason = rowReasons[index].orEmpty()

                val stripeColor = when (currentResult) {
                    "OK" -> QcOk
                    "NG" -> QcNg
                    "RW" -> QcRw
                    else -> QcBorder
                }

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, QcBorder, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = if (index % 2 == 0) QcSurface else QcSurfaceAlt),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(modifier = Modifier.fillMaxWidth()) {
                        // Left status stripe
                        Box(
                            modifier = Modifier
                                .width(6.dp)
                                .fillMaxHeight()
                                .background(stripeColor)
                        )

                        Column(
                            modifier = Modifier
                                .weight(1f)
                                .padding(12.dp)
                        ) {
                            // Test title
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = "${index + 1}.",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = QcMuted,
                                    modifier = Modifier.padding(end = 6.dp)
                                )
                                Text(
                                    text = testName,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = QcInk
                                )
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            // Photo Action Row
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Button(
                                    onClick = { launchCamera(index) },
                                    shape = RoundedCornerShape(6.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = if (hasPhoto) QcMuted else QcPrimary),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                                ) {
                                    Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(if (hasPhoto) "Retake" else "Camera", fontSize = 12.sp)
                                }

                                OutlinedButton(
                                    onClick = { launchGallery(index) },
                                    shape = RoundedCornerShape(6.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                                ) {
                                    Icon(Icons.Default.Folder, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Browse", fontSize = 12.sp)
                                }

                                Text(
                                    text = photoName,
                                    fontSize = 11.sp,
                                    color = if (hasPhoto) QcOk else QcMuted,
                                    fontWeight = if (hasPhoto) FontWeight.Bold else FontWeight.Normal
                                )

                                if (hasPhoto) {
                                    Text(
                                        text = "View",
                                        fontSize = 11.sp,
                                        color = QcPrimary,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier
                                            .clickable { previewPhotoUri = photoUris[index] }
                                            .padding(horizontal = 4.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // Result buttons: OK, NG, RW (locked until photo attached!)
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                val resultsList = listOf("OK" to QcOk, "NG" to QcNg, "RW" to QcRw)

                                for ((code, color) in resultsList) {
                                    val isSelected = currentResult == code
                                    val btnColor = if (!hasPhoto) {
                                        QcDisabled
                                    } else if (isSelected) {
                                        color
                                    } else {
                                        QcSurface
                                    }

                                    Button(
                                        onClick = {
                                            if (hasPhoto) {
                                                rowResults[index] = code
                                                if (code == "OK") {
                                                    rowReasons[index] = ""
                                                }
                                            } else {
                                                Toast.makeText(context, "Attach photo first", Toast.LENGTH_SHORT).show()
                                            }
                                        },
                                        enabled = hasPhoto,
                                        shape = RoundedCornerShape(4.dp),
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = btnColor,
                                            disabledContainerColor = Color(0xFFE2E8EE)
                                        ),
                                        border = if (hasPhoto && !isSelected) androidx.compose.foundation.BorderStroke(1.dp, color) else null,
                                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
                                    ) {
                                        Text(
                                            text = code,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            color = if (!hasPhoto) Color.Gray else if (isSelected) Color.White else color
                                        )
                                    }
                                }
                            }

                            // Defect reason entry (unlocked only if NG or RW)
                            val isReasonRequired = currentResult == "NG" || currentResult == "RW"
                            if (isReasonRequired) {
                                Spacer(modifier = Modifier.height(10.dp))
                                OutlinedTextField(
                                    value = currentReason,
                                    onValueChange = { rowReasons[index] = it },
                                    label = { Text(if (currentResult == "NG") "NG reason (required)" else "Rework defect (required)") },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedBorderColor = if (currentResult == "NG") QcNg else QcRw
                                    )
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    // Photo Preview Dialog
    if (previewPhotoUri != null) {
        Dialog(onDismissRequest = { previewPhotoUri = null }) {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = QcSurface),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Photo preview",
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        color = QcInk,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )

                    Text(
                        text = previewPhotoUri.toString(),
                        fontSize = 11.sp,
                        color = QcMuted,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )

                    Button(
                        onClick = { previewPhotoUri = null },
                        colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                    ) {
                        Text("Close")
                    }
                }
            }
        }
    }

    // Incomplete Validation Dialog
    if (saveIncompleteError != null) {
        AlertDialog(
            onDismissRequest = { saveIncompleteError = null },
            title = { Text("Inspection not complete") },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    Text("The following test(s) still need attention:\n")
                    for (item in saveIncompleteError!!.take(12)) {
                        Text("- $item", fontSize = 12.sp, color = QcNg)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = { saveIncompleteError = null },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("OK")
                }
            }
        )
    }

    // Exit Confirmation Dialog
    if (showExitConfirm) {
        AlertDialog(
            onDismissRequest = { showExitConfirm = false },
            title = { Text("Discard this inspection?") },
            text = { Text("Nothing has been saved yet. Leaving now loses the entries made on this sheet.\n\nDiscard and go back?") },
            confirmButton = {
                Button(
                    onClick = {
                        showExitConfirm = false
                        onFinished()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcNg)
                ) {
                    Text("Discard and exit")
                }
            },
            dismissButton = {
                TextButton(onClick = { showExitConfirm = false }) {
                    Text("Stay")
                }
            }
        )
    }
}
