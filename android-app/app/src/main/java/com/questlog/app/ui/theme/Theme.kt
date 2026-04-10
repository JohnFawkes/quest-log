package com.questlog.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val QuestPurple = Color(0xFF7C3AED)
private val QuestPurpleLight = Color(0xFFA78BFA)
private val QuestGold = Color(0xFFF59E0B)

private val DarkColors = darkColorScheme(
    primary = QuestPurple,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF4C1D95),
    secondary = QuestGold,
    onSecondary = Color.Black,
    background = Color(0xFF0F0F1A),
    surface = Color(0xFF1E1B2E),
    onBackground = Color.White,
    onSurface = Color.White,
    error = Color(0xFFEF4444),
)

@Composable
fun QuestLogTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkColors, content = content)
}
