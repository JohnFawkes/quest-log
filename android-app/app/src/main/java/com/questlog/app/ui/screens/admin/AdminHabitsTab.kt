package com.questlog.app.ui.screens.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.questlog.app.data.api.CreateHabitBody
import com.questlog.app.data.api.Habit
import com.questlog.app.data.api.User
import com.questlog.app.viewmodel.AdminViewModel

@Composable
fun AdminHabitsTab(vm: AdminViewModel, users: List<User>) {
    val state by vm.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    if (showCreateDialog) {
        CreateHabitDialog(
            users = users,
            onDismiss = { showCreateDialog = false },
            onConfirm = { body -> vm.createHabit(body); showCreateDialog = false },
        )
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Default.Add, "Create quest")
            }
        },
    ) { padding ->
        if (state.habits.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("No quests yet.", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item { Spacer(Modifier.height(8.dp)) }
                items(state.habits) { habit ->
                    HabitAdminCard(habit = habit, onDelete = { vm.deleteHabit(habit.id) })
                }
                item { Spacer(Modifier.height(72.dp)) }
            }
        }
    }
}

@Composable
private fun HabitAdminCard(habit: Habit, onDelete: () -> Unit) {
    var showConfirm by remember { mutableStateOf(false) }
    if (showConfirm) {
        AlertDialog(
            onDismissRequest = { showConfirm = false },
            title = { Text("Delete Quest?") },
            text = { Text("Delete \"${habit.name}\"? All quest history will be removed.") },
            confirmButton = {
                TextButton(onClick = { onDelete(); showConfirm = false },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { showConfirm = false }) { Text("Cancel") } },
        )
    }
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(habit.name, fontWeight = FontWeight.Medium)
                Text("${habit.scheduleType} • 💎${habit.pointsReward}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                Text(habit.assignedUsers.joinToString { it.name },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
            }
            IconButton(onClick = { showConfirm = true }) {
                Icon(Icons.Default.Delete, "Delete", tint = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun CreateHabitDialog(
    users: List<User>,
    onDismiss: () -> Unit,
    onConfirm: (CreateHabitBody) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var points by remember { mutableStateOf("10") }
    var scheduleType by remember { mutableStateOf("daily") }
    var selectedUserIds by remember { mutableStateOf(setOf<Int>()) }
    val scheduleTypes = listOf("daily", "weekly", "biweekly", "interval")

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create Quest") },
        text = {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 480.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("Quest name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = description, onValueChange = { description = it },
                    label = { Text("Description") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = points, onValueChange = { points = it },
                    label = { Text("Gem reward") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth())
                Text("Schedule", style = MaterialTheme.typography.labelMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    scheduleTypes.forEach { st ->
                        FilterChip(
                            selected = scheduleType == st, onClick = { scheduleType = st },
                            label = { Text(st, style = MaterialTheme.typography.bodySmall) },
                        )
                    }
                }
                Text("Assign Adventurers", style = MaterialTheme.typography.labelMedium)
                users.forEach { user ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = user.id in selectedUserIds,
                            onCheckedChange = {
                                selectedUserIds = if (it) selectedUserIds + user.id
                                                else selectedUserIds - user.id
                            },
                        )
                        Text(user.name)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                if (name.isBlank() || selectedUserIds.isEmpty()) return@TextButton
                onConfirm(CreateHabitBody(
                    name = name, description = description,
                    pointsReward = points.toIntOrNull() ?: 10,
                    coinsReward = 1, scheduleType = scheduleType,
                    scheduleDays = null, intervalDays = null,
                    penaltyEnabled = false, penaltyAmount = 0,
                    streakEnabled = false, streakMilestone = 5, streakMultiplier = 2.0,
                    coinsStreakBonus = 0, assignedUserIds = selectedUserIds.toList(),
                ))
            }) { Text("Create") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
