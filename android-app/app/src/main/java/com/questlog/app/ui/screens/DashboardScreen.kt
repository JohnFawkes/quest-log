package com.questlog.app.ui.screens

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.questlog.app.data.api.Habit
import com.questlog.app.data.api.TodayHabitEntry
import com.questlog.app.viewmodel.DashboardViewModel
import java.io.File

@Composable
fun DashboardScreen(vm: DashboardViewModel, serverUrl: String) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current

    var pendingHabit by remember { mutableStateOf<TodayHabitEntry?>(null) }
    var cameraImageFile by remember { mutableStateOf<File?>(null) }
    var showCompleteDialog by remember { mutableStateOf<TodayHabitEntry?>(null) }

    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let {
            val file = uriToFile(context, it)
            pendingHabit?.let { entry -> vm.completeHabit(entry.habit.id, file) }
            pendingHabit = null
        }
    }

    val cameraUri = remember { mutableStateOf<Uri?>(null) }
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) {
            pendingHabit?.let { entry -> vm.completeHabit(entry.habit.id, cameraImageFile) }
        }
        pendingHabit = null
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            val file = File(context.cacheDir.resolve("camera").also { it.mkdirs() }, "proof_${System.currentTimeMillis()}.jpg")
            cameraImageFile = file
            val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
            cameraUri.value = uri
            cameraLauncher.launch(uri)
        }
    }

    // Snackbar messages
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(state.successMessage) {
        state.successMessage?.let { snackbarHostState.showSnackbar(it); vm.clearMessage() }
    }
    LaunchedEffect(state.error) {
        state.error?.let { snackbarHostState.showSnackbar("Error: $it"); vm.clearMessage() }
    }

    // Complete-quest dialog
    showCompleteDialog?.let { entry ->
        AlertDialog(
            onDismissRequest = { showCompleteDialog = null },
            title = { Text(entry.habit.name) },
            text = { Text("How would you like to submit proof?") },
            confirmButton = {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = {
                        pendingHabit = entry
                        showCompleteDialog = null
                        if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                            val file = File(context.cacheDir.resolve("camera").also { it.mkdirs() }, "proof_${System.currentTimeMillis()}.jpg")
                            cameraImageFile = file
                            val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                            cameraUri.value = uri
                            cameraLauncher.launch(uri)
                        } else {
                            permissionLauncher.launch(Manifest.permission.CAMERA)
                        }
                    }) { Text("📷 Camera") }
                    TextButton(onClick = {
                        pendingHabit = entry
                        showCompleteDialog = null
                        galleryLauncher.launch("image/*")
                    }) { Text("🖼️ Gallery") }
                    TextButton(onClick = {
                        showCompleteDialog = null
                        vm.completeHabit(entry.habit.id, null)
                    }) { Text("✓ No Photo") }
                }
            },
            dismissButton = {
                TextButton(onClick = { showCompleteDialog = null }) { Text("Cancel") }
            },
        )
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbarHostState) }) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item { Spacer(Modifier.height(8.dp)) }

                if (state.todayHabits.isEmpty() && state.upcomingHabits.isEmpty()) {
                    item {
                        Box(Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                            Text("No quests assigned yet.", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                        }
                    }
                }

                if (state.todayHabits.isNotEmpty()) {
                    item {
                        Text("Today's Quests", style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold, modifier = Modifier.padding(vertical = 4.dp))
                    }
                    items(state.todayHabits) { entry ->
                        TodayHabitCard(
                            entry = entry,
                            serverUrl = serverUrl,
                            onComplete = { showCompleteDialog = entry },
                            completing = state.completingHabitId == entry.habit.id,
                        )
                    }
                }

                if (state.upcomingHabits.isNotEmpty()) {
                    item {
                        Text("Upcoming", style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 16.dp, bottom = 4.dp))
                    }
                    items(state.upcomingHabits) { entry ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Row(
                                Modifier.padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(entry.habit.name, fontWeight = FontWeight.Medium)
                                    entry.habit.description?.takeIf { it.isNotBlank() }?.let {
                                        Text(it, style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                                    }
                                }
                                Text("📅 ${entry.nextDue}", style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.secondary)
                            }
                        }
                    }
                }

                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }
}

@Composable
private fun TodayHabitCard(
    entry: TodayHabitEntry,
    serverUrl: String,
    onComplete: () -> Unit,
    completing: Boolean,
) {
    val completion = entry.completion
    val isDone = completion != null
    val statusColor = when (completion?.status) {
        "approved" -> MaterialTheme.colorScheme.secondary
        "pending" -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.error
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (isDone) MaterialTheme.colorScheme.surface.copy(alpha = 0.7f)
                            else MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row(
            Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(Modifier.weight(1f)) {
                Text(entry.habit.name, fontWeight = FontWeight.Medium)
                entry.habit.description?.takeIf { it.isNotBlank() }?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("💎 ${entry.habit.pointsReward}", style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary)
                    if (entry.streak > 0) {
                        Text("🔥 ${entry.streak}", style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error)
                    }
                    if (isDone) {
                        Text("● ${completion!!.status.replaceFirstChar { it.uppercase() }}",
                            style = MaterialTheme.typography.bodySmall, color = statusColor)
                    }
                }
            }
            if (!isDone) {
                if (completing) {
                    CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                } else {
                    Button(onClick = onComplete) { Text("Submit") }
                }
            } else {
                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = statusColor)
            }
        }
    }
}

private fun uriToFile(context: Context, uri: Uri): File {
    val stream = context.contentResolver.openInputStream(uri) ?: return File("")
    val file = File(context.cacheDir, "upload_${System.currentTimeMillis()}.jpg")
    file.outputStream().use { stream.copyTo(it) }
    return file
}
