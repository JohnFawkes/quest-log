package com.questlog.app.ui.screens.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.questlog.app.data.api.Reward
import com.questlog.app.viewmodel.AdminViewModel

@Composable
fun AdminRewardsTab(vm: AdminViewModel, rewards: List<Reward>) {
    val state by vm.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    if (showCreateDialog) {
        CreateRewardDialog(
            onDismiss = { showCreateDialog = false },
            onConfirm = { name, cost, desc, icon ->
                vm.createReward(name, cost, desc, icon)
                showCreateDialog = false
            },
        )
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Default.Add, "Create reward")
            }
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val pending = state.rewards.filter { it.isApproved == false }
            val approved = state.rewards.filter { it.isApproved == true }
            if (pending.isNotEmpty()) {
                item { Text("Pending Approval", style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp)) }
                items(pending) { reward -> RewardAdminCard(reward, vm) }
            }
            if (approved.isNotEmpty()) {
                item { Text("Active Rewards", style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp)) }
                items(approved) { reward -> RewardAdminCard(reward, vm) }
            }
            item { Spacer(Modifier.height(72.dp)) }
        }
    }
}

@Composable
private fun RewardAdminCard(reward: Reward, vm: AdminViewModel) {
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(reward.name, fontWeight = FontWeight.Medium)
                    if (reward.isApproved == false) {
                        Badge(containerColor = MaterialTheme.colorScheme.secondary) { Text("Pending") }
                    }
                }
                Text("💎 ${reward.cost}", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.secondary)
                reward.description?.takeIf { it.isNotBlank() }?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                }
            }
            if (reward.isApproved == false) {
                IconButton(onClick = { vm.approveReward(reward.id) }) {
                    Icon(Icons.Default.Check, "Approve", tint = MaterialTheme.colorScheme.secondary)
                }
            }
            IconButton(onClick = { vm.deleteReward(reward.id) }) {
                Icon(Icons.Default.Delete, "Delete", tint = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun CreateRewardDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, Int, String, String) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var cost by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var icon by remember { mutableStateOf("fas fa-gift") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create Reward") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = cost, onValueChange = { cost = it },
                    label = { Text("Cost (Gems)") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = description, onValueChange = { description = it },
                    label = { Text("Description") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = icon, onValueChange = { icon = it },
                    label = { Text("Icon (FontAwesome class)") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val c = cost.toIntOrNull() ?: return@TextButton
                if (name.isNotBlank() && c > 0) onConfirm(name, c, description, icon)
            }) { Text("Create") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
