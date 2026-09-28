package com.example.qcsystem.ui.builder

import android.widget.Toast
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
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.model.Checksheet
import com.example.qcsystem.model.ScanRule
import com.example.qcsystem.model.ScanTarget
import com.example.qcsystem.model.UnitField
import com.example.qcsystem.scanner.ScanningEngine
import com.example.qcsystem.scanner.ScanParseError
import com.example.qcsystem.theme.*
import com.example.qcsystem.ui.components.QcHeaderBar

@Composable
fun BuilderScreen(
    repository: DataRepository,
    initialSheetKey: String? = null,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val checksheetsSource by repository.checksheets.collectAsState()

    // Local mutable copy of all sheets
    val workingSheets = remember {
        mutableStateMapOf<String, Checksheet>().apply {
            checksheetsSource.forEach { (k, v) -> put(k, v) }
        }
    }

    var selectedSheetKey by remember {
        mutableStateOf(initialSheetKey ?: workingSheets.keys.firstOrNull() ?: "OQC")
    }

    var selectedTab by remember { mutableIntStateOf(0) }
    var isDirty by remember { mutableStateOf(false) }

    val currentSheet = workingSheets[selectedSheetKey]

    // Dialog states
    var showNewSheetDialog by remember { mutableStateOf(false) }
    var showCopySheetDialog by remember { mutableStateOf(false) }
    var showFieldDialog by remember { mutableStateOf<Pair<Int?, UnitField?>?>(null) } // index to field
    var showBulkTestsDialog by remember { mutableStateOf(false) }
    var showScanStepDialog by remember { mutableStateOf<Pair<Int?, ScanTarget?>?>(null) }

    fun updateCurrentSheet(newSheet: Checksheet) {
        workingSheets[selectedSheetKey] = newSheet
        isDirty = true
    }

    fun saveAll() {
        // Validation
        for ((key, sheet) in workingSheets) {
            if (sheet.name.isBlank()) {
                Toast.makeText(context, "[$key] Sheet needs a name", Toast.LENGTH_LONG).show()
                return
            }
            if (sheet.tests.isEmpty()) {
                Toast.makeText(context, "[$key] Add at least one test", Toast.LENGTH_LONG).show()
                return
            }
            val hasSerial = sheet.unitFields.any { it.id == "serial_number" }
            val hasBoard = sheet.unitFields.any { it.id == "main_board_no" }
            if (!hasSerial || !hasBoard) {
                Toast.makeText(context, "[$key] serial_number and main_board_no are required", Toast.LENGTH_LONG).show()
                return
            }
        }

        repository.saveChecksheets(workingSheets.toMap(), createBackup = true)
        isDirty = false
        Toast.makeText(context, "All check sheets saved (backup created).", Toast.LENGTH_SHORT).show()
    }

    if (currentSheet == null) {
        Scaffold(
            topBar = {
                QcHeaderBar(
                    title = "Check sheet builder",
                    subtitle = "Add check sheets, tests and scanner rules",
                    onBack = onBack
                )
            },
            containerColor = QcBackground
        ) { paddingValues ->
            Box(modifier = Modifier.fillMaxSize().padding(paddingValues), contentAlignment = Alignment.Center) {
                Text("No check sheets available")
            }
        }
        return
    }

    val activeSheet = currentSheet

    Scaffold(
        topBar = {
            QcHeaderBar(
                title = "Check sheet builder",
                subtitle = "Add check sheets, tests and scanner rules",
                onBack = {
                    if (isDirty) {
                        // Warn or direct exit
                        onBack()
                    } else {
                        onBack()
                    }
                },
                actions = {
                    Button(
                        onClick = { saveAll() },
                        colors = ButtonDefaults.buttonColors(containerColor = if (isDirty) QcOk else QcPrimary),
                        shape = RoundedCornerShape(4.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                    ) {
                        Text(if (isDirty) "Save changes *" else "Save all", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            )
        },
        containerColor = QcBackground
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Sheet Switcher Bar
            Surface(color = QcSurfaceAlt, modifier = Modifier.border(1.dp, QcBorder)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    var sheetMenuExpanded by remember { mutableStateOf(false) }
                    Box {
                        OutlinedButton(
                            onClick = { sheetMenuExpanded = true },
                            shape = RoundedCornerShape(6.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text("Sheet: ${activeSheet.key} (${activeSheet.testCount} tests)", color = QcInk, fontWeight = FontWeight.Bold)
                            Icon(Icons.Default.ArrowDropDown, null)
                        }

                        DropdownMenu(
                            expanded = sheetMenuExpanded,
                            onDismissRequest = { sheetMenuExpanded = false }
                        ) {
                            for (key in workingSheets.keys) {
                                DropdownMenuItem(
                                    text = { Text(key) },
                                    onClick = {
                                        selectedSheetKey = key
                                        sheetMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        IconButton(onClick = { showNewSheetDialog = true }) {
                            Icon(Icons.Default.Add, "New sheet", tint = QcPrimary)
                        }
                        IconButton(onClick = { showCopySheetDialog = true }) {
                            Icon(Icons.Default.ContentCopy, "Copy sheet", tint = QcPrimary)
                        }
                        if (workingSheets.size > 1) {
                            IconButton(onClick = {
                                workingSheets.remove(selectedSheetKey)
                                selectedSheetKey = workingSheets.keys.first()
                                isDirty = true
                            }) {
                                Icon(Icons.Default.Delete, "Delete sheet", tint = QcNg)
                            }
                        }
                    }
                }
            }

            // Tabs Bar: General, Unit fields, Tests, Scanning
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = QcSurface,
                contentColor = QcPrimary
            ) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("General", fontSize = 12.sp) })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Unit fields", fontSize = 12.sp) })
                Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 }, text = { Text("Tests (${activeSheet.testCount})", fontSize = 12.sp) })
                Tab(selected = selectedTab == 3, onClick = { selectedTab = 3 }, text = { Text("Scanning", fontSize = 12.sp) })
            }

            // Tab Content
            Box(
                modifier = Modifier
                    .weight(1f)
                    .padding(14.dp)
            ) {
                when (selectedTab) {
                    0 -> GeneralTab(
                        sheet = activeSheet,
                        onUpdate = { updateCurrentSheet(it) }
                    )
                    1 -> UnitFieldsTab(
                        sheet = activeSheet,
                        onAdd = { showFieldDialog = null to null },
                        onEdit = { index, field -> showFieldDialog = index to field },
                        onDelete = { index ->
                            val updated = activeSheet.unitFields.toMutableList().apply { removeAt(index) }
                            updateCurrentSheet(activeSheet.copy(unitFields = updated))
                        },
                        onMove = { from, to ->
                            val updated = activeSheet.unitFields.toMutableList()
                            val item = updated.removeAt(from)
                            updated.add(to, item)
                            updateCurrentSheet(activeSheet.copy(unitFields = updated))
                        }
                    )
                    2 -> TestsTab(
                        sheet = activeSheet,
                        onAdd = {
                            val updated = activeSheet.tests.toMutableList().apply { add("New test") }
                            updateCurrentSheet(activeSheet.copy(tests = updated))
                        },
                        onEdit = { index, newName ->
                            val updated = activeSheet.tests.toMutableList().apply { set(index, newName) }
                            updateCurrentSheet(activeSheet.copy(tests = updated))
                        },
                        onDelete = { index ->
                            val updated = activeSheet.tests.toMutableList().apply { removeAt(index) }
                            updateCurrentSheet(activeSheet.copy(tests = updated))
                        },
                        onMove = { from, to ->
                            val updated = activeSheet.tests.toMutableList()
                            val item = updated.removeAt(from)
                            updated.add(to, item)
                            updateCurrentSheet(activeSheet.copy(tests = updated))
                        },
                        onBulkPaste = { showBulkTestsDialog = true }
                    )
                    3 -> ScanningTab(
                        sheet = activeSheet,
                        onAdd = { showScanStepDialog = null to null },
                        onEdit = { index, target -> showScanStepDialog = index to target },
                        onDelete = { index ->
                            val updated = activeSheet.scanTargets.toMutableList().apply { removeAt(index) }
                            updateCurrentSheet(activeSheet.copy(scanTargets = updated))
                        }
                    )
                }
            }
        }
    }

    // Dialog: New Sheet
    if (showNewSheetDialog) {
        var newCode by remember { mutableStateOf("") }
        var newName by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showNewSheetDialog = false },
            title = { Text("New check sheet") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = newCode,
                        onValueChange = { newCode = it.uppercase() },
                        label = { Text("Short code (e.g. FQC)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text("Full name (e.g. FQC Check Sheet)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val key = newCode.trim()
                        if (key.isNotEmpty() && !workingSheets.containsKey(key)) {
                            val newSheet = Checksheet(
                                key = key,
                                name = newName.ifBlank { "$key Check Sheet" },
                                unitFields = listOf(
                                    UnitField("serial_number", "Serial number", required = true),
                                    UnitField("main_board_no", "Main board number", required = true),
                                    UnitField("model", "Model / size", required = true)
                                ),
                                scanTargets = listOf(
                                    ScanTarget(
                                        id = "unit_qr",
                                        label = "Unit QR code",
                                        prompt = "Scan unit QR code",
                                        rule = ScanRule(type = "raw", target = "serial_number")
                                    )
                                ),
                                tests = listOf("Appearance check", "Power on test")
                            )
                            workingSheets[key] = newSheet
                            selectedSheetKey = key
                            isDirty = true
                            showNewSheetDialog = false
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Create")
                }
            },
            dismissButton = {
                TextButton(onClick = { showNewSheetDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Dialog: Copy Sheet
    if (showCopySheetDialog) {
        var copyCode by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showCopySheetDialog = false },
            title = { Text("Copy check sheet") },
            text = {
                OutlinedTextField(
                    value = copyCode,
                    onValueChange = { copyCode = it.uppercase() },
                    label = { Text("New short code (e.g. ${activeSheet.key}_B)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        val key = copyCode.trim()
                        if (key.isNotEmpty() && !workingSheets.containsKey(key)) {
                            workingSheets[key] = activeSheet.copy(key = key, name = "${activeSheet.name} (Copy)")
                            selectedSheetKey = key
                            isDirty = true
                            showCopySheetDialog = false
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Copy")
                }
            },
            dismissButton = {
                TextButton(onClick = { showCopySheetDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Dialog: Add / Edit Unit Field
    if (showFieldDialog != null) {
        val (index, existingField) = showFieldDialog!!
        var label by remember { mutableStateOf(existingField?.label.orEmpty()) }
        var fieldId by remember { mutableStateOf(existingField?.id.orEmpty()) }
        var isRequired by remember { mutableStateOf(existingField?.required ?: false) }
        val isLocked = existingField?.isMandatory == true

        AlertDialog(
            onDismissRequest = { showFieldDialog = null },
            title = { Text(if (existingField != null) "Edit field" else "Add field") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = label,
                        onValueChange = {
                            label = it
                            if (existingField == null && !isLocked) {
                                fieldId = it.lowercase().filter { c -> c.isLetterOrDigit() || c == '_' }.replace(" ", "_")
                            }
                        },
                        label = { Text("Label shown to inspector") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = fieldId,
                        onValueChange = { if (!isLocked) fieldId = it.lowercase().filter { c -> c.isLetterOrDigit() || c == '_' } },
                        label = { Text("Field ID (lowercase, used by scanner rules)") },
                        enabled = !isLocked,
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = if (isLocked) true else isRequired,
                            onCheckedChange = { if (!isLocked) isRequired = it },
                            enabled = !isLocked
                        )
                        Text("Required before tests open", fontSize = 13.sp)
                    }

                    if (isLocked) {
                        Text("This is a built-in mandatory field.", color = QcMuted, fontSize = 11.sp)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (label.isNotBlank() && fieldId.isNotBlank()) {
                            val updatedFields = activeSheet.unitFields.toMutableList()
                            val newField = UnitField(fieldId, label, if (isLocked) true else isRequired)
                            if (index != null && index in updatedFields.indices) {
                                updatedFields[index] = newField
                            } else {
                                updatedFields.add(newField)
                            }
                            updateCurrentSheet(activeSheet.copy(unitFields = updatedFields))
                            showFieldDialog = null
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { showFieldDialog = null }) { Text("Cancel") }
            }
        )
    }

    // Dialog: Bulk Paste Tests (Excel compatible!)
    if (showBulkTestsDialog) {
        var bulkText by remember { mutableStateOf(activeSheet.tests.joinToString("\n")) }
        Dialog(onDismissRequest = { showBulkTestsDialog = false }) {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = QcSurface),
                modifier = Modifier.fillMaxWidth().fillMaxHeight(0.8f).padding(12.dp)
            ) {
                Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                    Text("Paste test list (Excel compatible)", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text("One test per line. Automatically strips leading numbers like 1. or 1) and tabs.", fontSize = 12.sp, color = QcMuted, modifier = Modifier.padding(vertical = 4.dp))

                    OutlinedTextField(
                        value = bulkText,
                        onValueChange = { bulkText = it },
                        modifier = Modifier.weight(1f).fillMaxWidth()
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                        horizontalArrangement = Arrangement.End
                    ) {
                        TextButton(onClick = { showBulkTestsDialog = false }) { Text("Cancel") }
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = {
                                val cleaned = bulkText.lines().mapNotNull { line ->
                                    var s = line.trim()
                                    // Strip leading 1. or 1)
                                    s = s.replaceFirst(Regex("^[0-9]+[.)]\\s*"), "").trim()
                                    if (s.isNotBlank()) s else null
                                }
                                if (cleaned.isNotEmpty()) {
                                    updateCurrentSheet(activeSheet.copy(tests = cleaned))
                                    showBulkTestsDialog = false
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                        ) {
                            Text("Replace test list")
                        }
                    }
                }
            }
        }
    }

    // Dialog: Scan Step Configurator with Sandbox Test
    if (showScanStepDialog != null) {
        val (index, existingTarget) = showScanStepDialog!!
        ScanStepConfigDialog(
            sheet = activeSheet,
            target = existingTarget,
            onDismiss = { showScanStepDialog = null },
            onSave = { newTarget ->
                val updated = activeSheet.scanTargets.toMutableList()
                if (index != null && index in updated.indices) {
                    updated[index] = newTarget
                } else {
                    updated.add(newTarget)
                }
                updateCurrentSheet(activeSheet.copy(scanTargets = updated))
                showScanStepDialog = null
            }
        )
    }
}

@Composable
private fun GeneralTab(
    sheet: Checksheet,
    onUpdate: (Checksheet) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(8.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("General settings", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = QcInk)

        OutlinedTextField(
            value = sheet.name,
            onValueChange = { onUpdate(sheet.copy(name = it)) },
            label = { Text("Check sheet name") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = sheet.subtitle,
            onValueChange = { onUpdate(sheet.copy(subtitle = it)) },
            label = { Text("Subtitle / Context") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Card(
            modifier = Modifier.fillMaxWidth().border(1.dp, QcBorder, RoundedCornerShape(8.dp)),
            colors = CardDefaults.cardColors(containerColor = QcSurface)
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text("Summary", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Spacer(modifier = Modifier.height(4.dp))
                Text("Short Code: ${sheet.key}", fontSize = 12.sp, color = QcMuted)
                Text("Total Tests: ${sheet.testCount}", fontSize = 12.sp, color = QcMuted)
                Text("Unit Fields: ${sheet.unitFields.size}", fontSize = 12.sp, color = QcMuted)
                Text("Scan Steps: ${sheet.scanTargets.size}", fontSize = 12.sp, color = QcMuted)
            }
        }
    }
}

@Composable
private fun UnitFieldsTab(
    sheet: Checksheet,
    onAdd: () -> Unit,
    onEdit: (Int, UnitField) -> Unit,
    onDelete: (Int) -> Unit,
    onMove: (Int, Int) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Unit detail fields", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Button(
                onClick = onAdd,
                shape = RoundedCornerShape(6.dp),
                colors = ButtonDefaults.buttonColors(containerColor = QcPrimary),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Icon(Icons.Default.Add, null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Add field", fontSize = 12.sp)
            }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(sheet.unitFields) { index, field ->
                Card(
                    modifier = Modifier.fillMaxWidth().border(1.dp, QcBorder, RoundedCornerShape(6.dp)),
                    colors = CardDefaults.cardColors(containerColor = QcSurface)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f).clickable { onEdit(index, field) }) {
                            Text(field.label + if (field.required) " *" else "", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("ID: ${field.id}", fontSize = 11.sp, color = QcMuted)
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (index > 0) {
                                IconButton(onClick = { onMove(index, index - 1) }, modifier = Modifier.size(32.dp)) {
                                    Icon(Icons.Default.KeyboardArrowUp, "Move up")
                                }
                            }
                            if (index < sheet.unitFields.size - 1) {
                                IconButton(onClick = { onMove(index, index + 1) }, modifier = Modifier.size(32.dp)) {
                                    Icon(Icons.Default.KeyboardArrowDown, "Move down")
                                }
                            }
                            IconButton(onClick = { onEdit(index, field) }, modifier = Modifier.size(32.dp)) {
                                Icon(Icons.Default.Edit, "Edit", tint = QcPrimary)
                            }
                            if (!field.isMandatory) {
                                IconButton(onClick = { onDelete(index) }, modifier = Modifier.size(32.dp)) {
                                    Icon(Icons.Default.Delete, "Delete", tint = QcNg)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TestsTab(
    sheet: Checksheet,
    onAdd: () -> Unit,
    onEdit: (Int, String) -> Unit,
    onDelete: (Int) -> Unit,
    onMove: (Int, Int) -> Unit,
    onBulkPaste: () -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Tests in order", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedButton(
                    onClick = onBulkPaste,
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text("Paste list", fontSize = 11.sp)
                }
                Button(
                    onClick = onAdd,
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text("Add test", fontSize = 11.sp)
                }
            }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            itemsIndexed(sheet.tests) { index, testName ->
                var editingName by remember { mutableStateOf(testName) }
                var isEditingThis by remember { mutableStateOf(false) }

                Card(
                    modifier = Modifier.fillMaxWidth().border(1.dp, QcBorder, RoundedCornerShape(6.dp)),
                    colors = CardDefaults.cardColors(containerColor = QcSurface)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("${index + 1}.", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = QcMuted, modifier = Modifier.width(28.dp))

                        if (isEditingThis) {
                            OutlinedTextField(
                                value = editingName,
                                onValueChange = { editingName = it },
                                modifier = Modifier.weight(1f),
                                singleLine = true
                            )
                            IconButton(onClick = {
                                onEdit(index, editingName)
                                isEditingThis = false
                            }) {
                                Icon(Icons.Default.Check, "Save", tint = QcOk)
                            }
                        } else {
                            Text(testName, fontSize = 13.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f).clickable { isEditingThis = true })
                            Row {
                                if (index > 0) {
                                    IconButton(onClick = { onMove(index, index - 1) }, modifier = Modifier.size(28.dp)) {
                                        Icon(Icons.Default.KeyboardArrowUp, null)
                                    }
                                }
                                if (index < sheet.tests.size - 1) {
                                    IconButton(onClick = { onMove(index, index + 1) }, modifier = Modifier.size(28.dp)) {
                                        Icon(Icons.Default.KeyboardArrowDown, null)
                                    }
                                }
                                IconButton(onClick = { onDelete(index) }, modifier = Modifier.size(28.dp)) {
                                    Icon(Icons.Default.Delete, null, tint = QcNg)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ScanningTab(
    sheet: Checksheet,
    onAdd: () -> Unit,
    onEdit: (Int, ScanTarget) -> Unit,
    onDelete: (Int) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Scan targets", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Button(
                onClick = onAdd,
                shape = RoundedCornerShape(6.dp),
                colors = ButtonDefaults.buttonColors(containerColor = QcPrimary),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Icon(Icons.Default.Add, null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Add scan step", fontSize = 12.sp)
            }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(sheet.scanTargets) { index, target ->
                Card(
                    modifier = Modifier.fillMaxWidth().border(1.dp, QcBorder, RoundedCornerShape(6.dp)),
                    colors = CardDefaults.cardColors(containerColor = QcSurface)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f).clickable { onEdit(index, target) }) {
                            Text(target.label, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("Rule: ${ScanningEngine.describeRule(target.rule)}", fontSize = 11.sp, color = QcPrimary)
                            Text("Prompt: ${target.prompt}", fontSize = 11.sp, color = QcMuted)
                        }

                        Row {
                            IconButton(onClick = { onEdit(index, target) }, modifier = Modifier.size(32.dp)) {
                                Icon(Icons.Default.Edit, "Edit", tint = QcPrimary)
                            }
                            IconButton(onClick = { onDelete(index) }, modifier = Modifier.size(32.dp)) {
                                Icon(Icons.Default.Delete, "Delete", tint = QcNg)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ScanStepConfigDialog(
    sheet: Checksheet,
    target: ScanTarget?,
    onDismiss: () -> Unit,
    onSave: (ScanTarget) -> Unit
) {
    var label by remember { mutableStateOf(target?.label.orEmpty()) }
    var prompt by remember { mutableStateOf(target?.prompt.orEmpty()) }
    var ruleType by remember { mutableStateOf(target?.rule?.type ?: "raw") }
    var targetField by remember { mutableStateOf(target?.rule?.target.orEmpty().ifBlank { sheet.unitFields.firstOrNull()?.id.orEmpty() }) }
    var separator by remember { mutableStateOf(target?.rule?.separator ?: ";") }
    var pairSeparator by remember { mutableStateOf(target?.rule?.pairSeparator ?: ":") }
    var mapText by remember { mutableStateOf(ScanningEngine.mappingToText(target?.rule?.map ?: emptyMap())) }
    var slicesText by remember { mutableStateOf(ScanningEngine.slicesToText(target?.rule?.slices ?: emptyMap())) }
    var regexPattern by remember { mutableStateOf(target?.rule?.pattern.orEmpty()) }

    var testCodeInput by remember { mutableStateOf("") }
    var testResultOutput by remember { mutableStateOf("") }
    var testResultColor by remember { mutableStateOf(QcMuted) }

    fun buildRule(): ScanRule {
        return ScanRule(
            type = ruleType,
            target = targetField,
            separator = separator,
            pairSeparator = pairSeparator,
            map = ScanningEngine.textToMapping(mapText),
            slices = ScanningEngine.textToSlices(slicesText),
            pattern = regexPattern
        )
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier.fillMaxWidth().fillMaxHeight(0.9f),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = QcSurface)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(if (target != null) "Edit scan step" else "Add scan step", fontWeight = FontWeight.Bold, fontSize = 16.sp)

                OutlinedTextField(
                    value = label,
                    onValueChange = { label = it },
                    label = { Text("Step name (e.g. Unit QR code)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    label = { Text("Prompt shown to inspector") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Rule Type Dropdown
                var ruleTypeDropdown by remember { mutableStateOf(false) }
                Box {
                    OutlinedButton(
                        onClick = { ruleTypeDropdown = true },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text("How code is read: $ruleType")
                    }
                    DropdownMenu(
                        expanded = ruleTypeDropdown,
                        onDismissRequest = { ruleTypeDropdown = false }
                    ) {
                        for (type in listOf("raw", "delimited", "split", "regex", "json", "fixed")) {
                            DropdownMenuItem(text = { Text(type) }, onClick = {
                                ruleType = type
                                ruleTypeDropdown = false
                            })
                        }
                    }
                }

                when (ruleType) {
                    "raw" -> {
                        var targetDropdown by remember { mutableStateOf(false) }
                        Box {
                            OutlinedButton(onClick = { targetDropdown = true }, modifier = Modifier.fillMaxWidth()) {
                                Text("Puts code into: $targetField")
                            }
                            DropdownMenu(expanded = targetDropdown, onDismissRequest = { targetDropdown = false }) {
                                for (f in sheet.unitFields) {
                                    DropdownMenuItem(text = { Text("${f.label} (${f.id})") }, onClick = {
                                        targetField = f.id
                                        targetDropdown = false
                                    })
                                }
                            }
                        }
                    }
                    "delimited" -> {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(value = separator, onValueChange = { separator = it }, label = { Text("Item Sep") }, modifier = Modifier.weight(1f))
                            OutlinedTextField(value = pairSeparator, onValueChange = { pairSeparator = it }, label = { Text("Pair Sep") }, modifier = Modifier.weight(1f))
                        }
                        Text("Mapping (e.g. SN = serial_number)", fontSize = 11.sp, color = QcMuted)
                        OutlinedTextField(value = mapText, onValueChange = { mapText = it }, modifier = Modifier.fillMaxWidth())
                    }
                    "split" -> {
                        OutlinedTextField(value = separator, onValueChange = { separator = it }, label = { Text("Separator (e.g. ,)") }, modifier = Modifier.fillMaxWidth())
                        Text("Position mapping (e.g. 0 = serial_number)", fontSize = 11.sp, color = QcMuted)
                        OutlinedTextField(value = mapText, onValueChange = { mapText = it }, modifier = Modifier.fillMaxWidth())
                    }
                    "fixed" -> {
                        Text("Character slices (e.g. serial_number = 0, 20)", fontSize = 11.sp, color = QcMuted)
                        OutlinedTextField(value = slicesText, onValueChange = { slicesText = it }, modifier = Modifier.fillMaxWidth())
                    }
                    "regex" -> {
                        OutlinedTextField(value = regexPattern, onValueChange = { regexPattern = it }, label = { Text("Pattern with (?P<field>...)") }, modifier = Modifier.fillMaxWidth())
                    }
                    "json" -> {
                        Text("JSON key mapping (e.g. sn = serial_number)", fontSize = 11.sp, color = QcMuted)
                        OutlinedTextField(value = mapText, onValueChange = { mapText = it }, modifier = Modifier.fillMaxWidth())
                    }
                }

                // Sandbox: Try a real code!
                Card(
                    modifier = Modifier.fillMaxWidth().border(1.dp, QcBorder, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = QcSurfaceAlt)
                ) {
                    Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Try a real code", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            OutlinedTextField(
                                value = testCodeInput,
                                onValueChange = { testCodeInput = it },
                                placeholder = { Text("Paste code to test...") },
                                modifier = Modifier.weight(1f),
                                singleLine = true
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Button(
                                onClick = {
                                    try {
                                        val parsed = ScanningEngine.parseScan(testCodeInput, buildRule())
                                        testResultOutput = "Success:\n" + parsed.entries.joinToString("\n") { "${it.key}: ${it.value}" }
                                        testResultColor = QcOk
                                    } catch (e: Exception) {
                                        testResultOutput = "Error: ${e.message}"
                                        testResultColor = QcNg
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                            ) {
                                Text("Test")
                            }
                        }

                        if (testResultOutput.isNotEmpty()) {
                            Text(testResultOutput, fontSize = 11.sp, color = testResultColor)
                        }
                    }
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onDismiss) { Text("Cancel") }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            if (label.isNotBlank()) {
                                onSave(
                                    ScanTarget(
                                        id = target?.id ?: label.lowercase().replace(" ", "_"),
                                        label = label,
                                        prompt = prompt.ifBlank { "Scan the $label" },
                                        rule = buildRule()
                                    )
                                )
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                    ) {
                        Text("Save step")
                    }
                }
            }
        }
    }
}
