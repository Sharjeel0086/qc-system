package com.example.qcsystem.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.model.Inspection
import com.example.qcsystem.model.InspectionWithResults
import com.example.qcsystem.theme.*
import com.example.qcsystem.ui.components.QcHeaderBar
import com.example.qcsystem.ui.components.QcStatusBadge

@Composable
fun RecordsScreen(
    repository: DataRepository,
    onBack: () -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedSheetFilter by remember { mutableStateOf("All sheets") }
    val checksheets by repository.checksheets.collectAsState()
    val sheetNames = remember(checksheets) { listOf("All sheets") + checksheets.values.map { it.name } }

    var inspections by remember { mutableStateOf<List<Inspection>>(emptyList()) }
    var selectedInspectionDetail by remember { mutableStateOf<InspectionWithResults?>(null) }

    fun refreshList() {
        val filterKey = checksheets.entries.find { it.value.name == selectedSheetFilter }?.key.orEmpty()
        inspections = repository.listInspections(searchQuery, filterKey)
    }

    LaunchedEffect(searchQuery, selectedSheetFilter) {
        refreshList()
    }

    Scaffold(
        topBar = {
            QcHeaderBar(
                title = "Saved records",
                subtitle = "Search and review completed inspections",
                onBack = onBack
            )
        },
        containerColor = QcBackground
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 14.dp, vertical = 12.dp)
        ) {
            // Search & Filter Box
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, QcBorder, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = QcSurface),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { searchQuery = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("Search by serial, board, or inspector...") },
                        leadingIcon = { Icon(Icons.Default.Search, null, tint = QcMuted) },
                        trailingIcon = {
                            if (searchQuery.isNotEmpty()) {
                                IconButton(onClick = { searchQuery = "" }) {
                                    Icon(Icons.Default.Close, null, tint = QcMuted)
                                }
                            }
                        },
                        singleLine = true
                    )

                    var sheetDropdownExpanded by remember { mutableStateOf(false) }
                    Box(modifier = Modifier.fillMaxWidth()) {
                        OutlinedButton(
                            onClick = { sheetDropdownExpanded = true },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(6.dp)
                        ) {
                            Text("Sheet: $selectedSheetFilter", color = QcInk)
                        }

                        DropdownMenu(
                            expanded = sheetDropdownExpanded,
                            onDismissRequest = { sheetDropdownExpanded = false }
                        ) {
                            for (name in sheetNames) {
                                DropdownMenuItem(
                                    text = { Text(name) },
                                    onClick = {
                                        selectedSheetFilter = name
                                        sheetDropdownExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }
            }

            Text(
                text = "${inspections.size} record(s) found",
                fontSize = 12.sp,
                color = QcMuted,
                modifier = Modifier.padding(vertical = 10.dp)
            )

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(inspections, key = { it.id }) { insp ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .border(1.dp, QcBorder, RoundedCornerShape(8.dp))
                            .clickable {
                                selectedInspectionDetail = repository.getInspection(insp.id)
                            },
                        colors = CardDefaults.cardColors(containerColor = QcSurface)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Serial: ${insp.serialNumber}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = QcInk
                                )
                                QcStatusBadge(status = insp.overallResult)
                            }

                            Spacer(modifier = Modifier.height(4.dp))

                            Text(
                                text = insp.checksheetName,
                                fontSize = 12.sp,
                                color = QcPrimary,
                                fontWeight = FontWeight.SemiBold
                            )

                            if (insp.mainBoardNo.isNotBlank()) {
                                Text(
                                    text = "Main Board: ${insp.mainBoardNo}",
                                    fontSize = 11.sp,
                                    color = QcMuted
                                )
                            }

                            Spacer(modifier = Modifier.height(6.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "Inspector: ${insp.operatorName}",
                                    fontSize = 11.sp,
                                    color = QcMuted
                                )
                                Text(
                                    text = "OK: ${insp.okCount}  NG: ${insp.ngCount}  RW: ${insp.rwCount}",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = QcInk
                                )
                            }

                            Text(
                                text = insp.savedAt.replace("T", "  "),
                                fontSize = 10.sp,
                                color = QcMuted,
                                modifier = Modifier.padding(top = 4.dp)
                            )
                        }
                    }
                }
            }
        }
    }

    // Detail Dialog
    if (selectedInspectionDetail != null) {
        val detail = selectedInspectionDetail!!
        Dialog(onDismissRequest = { selectedInspectionDetail = null }) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxHeight(0.85f),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = QcSurface)
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    // Header
                    Surface(color = QcHeader) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = detail.inspection.checksheetName,
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                                Text(
                                    text = "Serial: ${detail.inspection.serialNumber}  |  Board: ${detail.inspection.mainBoardNo}",
                                    color = Color(0xFF9DB0C0),
                                    fontSize = 11.sp
                                )
                            }
                            IconButton(onClick = { selectedInspectionDetail = null }) {
                                Icon(Icons.Default.Close, null, tint = Color.White)
                            }
                        }
                    }

                    // Summary Bar
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(QcSurfaceAlt)
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        QcStatusBadge(status = detail.inspection.overallResult)
                        Text(
                            text = "OK ${detail.inspection.okCount}   NG ${detail.inspection.ngCount}   RW ${detail.inspection.rwCount} of ${detail.inspection.totalTests} tests",
                            fontSize = 11.sp,
                            color = QcMuted
                        )
                    }

                    // Test Results List
                    LazyColumn(
                        modifier = Modifier
                            .weight(1f)
                            .padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(detail.results) { res ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .border(1.dp, QcBorder, RoundedCornerShape(6.dp)),
                                colors = CardDefaults.cardColors(containerColor = QcSurface)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(10.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = "${res.testOrder}. ${res.testName}",
                                            fontWeight = FontWeight.SemiBold,
                                            fontSize = 13.sp,
                                            color = QcInk
                                        )
                                        if (res.reason.isNotBlank()) {
                                            Text(
                                                text = "Defect: ${res.reason}",
                                                fontSize = 11.sp,
                                                color = QcNg
                                            )
                                        }
                                        if (res.photoPath.isNotBlank()) {
                                            Text(
                                                text = "Photo: attached",
                                                fontSize = 10.sp,
                                                color = QcOk
                                            )
                                        }
                                    }

                                    QcStatusBadge(status = res.result)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
