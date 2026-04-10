package com.questlog.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.User
import com.questlog.app.viewmodel.AuthViewModel
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(
    user: User,
    token: String,
    repo: QuestLogRepository,
    authVm: AuthViewModel,
) {
    var name by remember(user) { mutableStateOf(user.name) }
    var selectedTheme by remember(user) { mutableStateOf(user.theme ?: "dark") }
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }
    val themes = listOf("dark", "princess", "forest")

    Scaffold(snackbarHost = { SnackbarHost(snackbarHostState) }) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Adventurer Settings", style = MaterialTheme.typography.headlineSmall)

            OutlinedTextField(
                value = name, onValueChange = { name = it },
                label = { Text("Display Name") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )

            Text("Theme", style = MaterialTheme.typography.labelLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                themes.forEach { theme ->
                    FilterChip(
                        selected = selectedTheme == theme,
                        onClick = { selectedTheme = theme },
                        label = { Text(theme.replaceFirstChar { it.uppercase() }) },
                    )
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        try {
                            val resp = repo.updateSettings(token, name = name.trim(), theme = selectedTheme)
                            if (resp.isSuccessful && resp.body() != null) {
                                authVm.updateUser(resp.body()!!.user)
                                snackbarHostState.showSnackbar("Settings saved!")
                            } else {
                                snackbarHostState.showSnackbar("Failed to save settings")
                            }
                        } catch (e: Exception) {
                            snackbarHostState.showSnackbar("Error: ${e.message}")
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Save") }

            Spacer(Modifier.weight(1f))

            Divider()

            OutlinedButton(
                onClick = { authVm.logout() },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
            ) { Text("Log Out") }

            Text("Server: ${user.email}", style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f))
        }
    }
}
