package com.example.qcsystem.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColorScheme = lightColorScheme(
    primary = QcPrimary,
    onPrimary = QcSurface,
    primaryContainer = QcSurfaceAlt,
    onPrimaryContainer = QcPrimaryDark,
    secondary = QcPrimaryDark,
    onSecondary = QcSurface,
    background = QcBackground,
    onBackground = QcInk,
    surface = QcSurface,
    onSurface = QcInk,
    surfaceVariant = QcSurfaceAlt,
    onSurfaceVariant = QcMuted,
    outline = QcBorder,
    error = QcNg,
    onError = QcSurface
)

private val DarkColorScheme = darkColorScheme(
    primary = QcPrimary,
    onPrimary = QcSurface,
    secondary = QcPrimaryDark,
    background = QcHeader,
    surface = QcHeader,
    onBackground = QcSurface,
    onSurface = QcSurface,
    error = QcNg
)

@Composable
fun QCSystemTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = QcHeader.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
