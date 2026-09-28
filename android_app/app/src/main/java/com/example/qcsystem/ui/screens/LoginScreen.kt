package com.example.qcsystem.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.qcsystem.auth.AuthManager
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.theme.*

@Composable
fun LoginScreen(
    repository: DataRepository,
    onLoginSuccess: () -> Unit
) {
    var username by remember { mutableStateOf("admin") }
    var password by remember { mutableStateOf("admin123") }
    var passwordVisible by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }

    fun attemptLogin() {
        errorMessage = ""
        val user = repository.getUserByUsername(username)
        if (user != null && AuthManager.verifyPassword(password, user.passwordHash, user.salt)) {
            repository.setCurrentUser(user)
            onLoginSuccess()
        } else {
            errorMessage = "That username and password combination was not recognised. Check both and try again."
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(QcBackground)
            .padding(16.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .widthIn(max = 480.dp),
            colors = CardDefaults.cardColors(containerColor = QcSurface),
            shape = RoundedCornerShape(12.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(28.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = "Quality Cross-Check System",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = QcInk
                )
                Text(
                    text = "LED unit inspection - sign in to continue",
                    fontSize = 13.sp,
                    color = QcMuted,
                    modifier = Modifier.padding(top = 4.dp, bottom = 24.dp)
                )

                Text(
                    text = "Username",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = QcInk,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                OutlinedTextField(
                    value = username,
                    onValueChange = { username = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = QcPrimary,
                        unfocusedBorderColor = QcBorder
                    )
                )

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "Password",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = QcInk,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                    trailingIcon = {
                        IconButton(onClick = { passwordVisible = !passwordVisible }) {
                            Icon(
                                imageVector = if (passwordVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                contentDescription = if (passwordVisible) "Hide password" else "Show password",
                                tint = QcMuted
                            )
                        }
                    },
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { attemptLogin() }),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = QcPrimary,
                        unfocusedBorderColor = QcBorder
                    )
                )

                if (errorMessage.isNotEmpty()) {
                    Text(
                        text = errorMessage,
                        color = QcNg,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(top = 10.dp)
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = { attemptLogin() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = QcPrimary)
                ) {
                    Text(
                        text = "Sign in",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }

                Spacer(modifier = Modifier.height(18.dp))

                Text(
                    text = "First run? Use admin / admin123 and change it from the settings menu.",
                    fontSize = 11.sp,
                    color = QcMuted
                )
            }
        }
    }
}
