package com.example.qcsystem.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.example.qcsystem.auth.AuthManager
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.model.Checksheet
import com.example.qcsystem.theme.*
import com.example.qcsystem.ui.components.QcHeaderBar

@Composable
fun SelectScreen(
    repository: DataRepository,
    onSelectSheet: (String) -> Unit,
    onOpenRecords: () -> Unit,
    onOpenBuilder: () -> Unit,
    onSignOut: () -> Unit
) {
    val context = LocalContext.current
    val currentUser by repository.currentUser.collectAsState()
    val checksheetsMap by repository.checksheets.collectAsState()
    val checksheets = remember(checksheetsMap) { checksheetsMap.values.toList() }

    var showMenu by remember { mutableStateOf(false) }
    var showAddInspectorDialog by remember { mutableStateOf(false) }
    var showChangePasswordDialog by remember { mutableStateOf(false) }

    val userName = currentUser?.fullName?.ifBlank { currentUser?.username } ?: "Inspector"
    val userRole = currentUser?.role ?: "inspector"

    Scaffold(
        topBar = {
            QcHeaderBar(
                title = "Quality Cross-Check System",
                subtitle = "Signed in as $userName ($userRole)",
                actions = {
                    IconButton(onClick = { showMenu = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "Menu", tint = Color.White)
                    }

                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Saved records") },
                            leadingIcon = { Icon(Icons.Default.History, null) },
                            onClick = {
                                showMenu = false
                                onOpenRecords()
                            }
                        )

                        if (userRole == "admin") {
                            DropdownMenuItem(
                                text = { Text("Check sheet builder") },
                                leadingIcon = { Icon(Icons.Default.Build, null) },
                                onClick = {
                                    showMenu = false
                                    onOpenBuilder()
                                }
                            )

                            DropdownMenuItem(
                                text = { Text("Add inspector") },
                                leadingIcon = { Icon(Icons.Default.PersonAdd, null) },
                                onClick = {
                                    showMenu = false
                                    showAddInspectorDialog = true
                                }
                            )
                        }

                        DropdownMenuItem(
                            text = { Text("Change my password") },
                            leadingIcon = { Icon(Icons.Default.Lock, null) },
                            onClick = {
                                showMenu = false
                                showChangePasswordDialog = true
                            }
                        )

                        HorizontalDivider()

                        DropdownMenuItem(
                            text = { Text("Sign out", color = QcNg) },
                            leadingIcon = { Icon(Icons.Default.ExitToApp, null, tint = QcNg) },
                            onClick = {
                                showMenu = false
                                onSignOut()
                            }
                        )
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
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Text(
                text = "Select a check sheet",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = QcInk,
                modifier = Modifier.padding(top = 4.dp)
            )
            Text(
                text = "Tap a sheet to start a new inspection.",
                fontSize = 13.sp,
                color = QcMuted,
                modifier = Modifier.padding(bottom = 16.dp)
            )

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(checksheets, key = { it.key }) { sheet ->
                    ChecksheetCard(sheet = sheet, onClick = { onSelectSheet(sheet.key) })
                }
            }
        }
    }

    // Dialog: Add Inspector
    if (showAddInspectorDialog) {
        var newUsername by remember { mutableStateOf("") }
        var newFullName by remember { mutableStateOf("") }
        var newPassword by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showAddInspectorDialog = false },
            title = { Text("Add inspector") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = newUsername,
                        onValueChange = { newUsername = it },
                        label = { Text("Username") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newFullName,
                        onValueChange = { newFullName = it },
                        label = { Text("Full name (optional)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newPassword,
                        onValueChange = { newPassword = it },
                        label = { Text("Password") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newUsername.isNotBlank() && newPassword.length >= 4) {
                            try {
                                repository.createUser(newUsername, newPassword, newFullName, "inspector")
                                Toast.makeText(context, "$newUsername added as inspector", Toast.LENGTH_SHORT).show()
                                showAddInspectorDialog = false
                            } catch (e: Exception) {
                                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                            }
                        } else {
                            Toast.makeText(context, "Username required, password min 4 chars", Toast.LENGTH_SHORT).show()
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Add")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddInspectorDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Dialog: Change Password
    if (showChangePasswordDialog) {
        var currentPass by remember { mutableStateOf("") }
        var newPass by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showChangePasswordDialog = false },
            title = { Text("Change my password") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = currentPass,
                        onValueChange = { currentPass = it },
                        label = { Text("Current password") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newPass,
                        onValueChange = { newPass = it },
                        label = { Text("New password (min 4 chars)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val user = currentUser
                        if (user != null) {
                            if (AuthManager.verifyPassword(currentPass, user.passwordHash, user.salt)) {
                                if (newPass.length >= 4) {
                                    repository.setPassword(user.username, newPass)
                                    Toast.makeText(context, "Password updated successfully", Toast.LENGTH_SHORT).show()
                                    showChangePasswordDialog = false
                                } else {
                                    Toast.makeText(context, "New password too short (min 4)", Toast.LENGTH_SHORT).show()
                                }
                            } else {
                                Toast.makeText(context, "Current password incorrect", Toast.LENGTH_SHORT).show()
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { showChangePasswordDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun ChecksheetCard(
    sheet: Checksheet,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .border(1.dp, QcBorder, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = QcSurface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = sheet.key,
                color = QcPrimary,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = sheet.name,
                color = QcInk,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = 3.dp)
            )
            if (sheet.subtitle.isNotEmpty()) {
                Text(
                    text = sheet.subtitle,
                    color = QcMuted,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            val scanNote = if (sheet.scanTargets.isNotEmpty()) "${sheet.scanTargets.size} scan step(s)" else "manual entry"
            Text(
                text = "${sheet.testCount} tests   |   $scanNote",
                color = QcMuted,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}
