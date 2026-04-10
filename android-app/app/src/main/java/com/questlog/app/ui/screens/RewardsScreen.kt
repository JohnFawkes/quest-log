package com.questlog.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.questlog.app.data.api.Reward
import com.questlog.app.viewmodel.RewardsViewModel

@Composable
fun RewardsScreen(vm: RewardsViewModel) {
    val state by vm.state.collectAsState()
    var showRequestDialog by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.successMessage) {
        state.successMessage?.let { snackbarHostState.showSnackbar(it); vm.clearMessage() }
    }
    LaunchedEffect(state.error) {
        state.error?.let { snackbarHostState.showSnackbar("Error: $it"); vm.clearMessage() }
    }

    if (showRequestDialog) {
        RequestRewardDialog(
            onDismiss = { showRequestDialog = false },
            onSubmit = { name, cost, desc ->
                vm.requestReward(name, cost, desc)
                showRequestDialog = false
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            FloatingActionButton(onClick = { showRequestDialog = true }) {
                Icon(Icons.Default.Add, "Request reward")
            }
        },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                    ) {
                        Text("💎 ${state.points} Gems available",
                            modifier = Modifier.padding(16.dp),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold)
                    }
                }
                item { Spacer(Modifier.height(4.dp)) }
                if (state.rewards.isEmpty()) {
                    item {
                        Text("No rewards available yet.", Modifier.padding(top = 32.dp),
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                    }
                }
                items(state.rewards) { reward ->
                    RewardCard(
                        reward = reward,
                        userPoints = state.points,
                        onRedeem = { vm.redeem(reward.id) },
                    )
                }
                item { Spacer(Modifier.height(72.dp)) }
            }
        }
    }
}

@Composable
private fun RewardCard(reward: Reward, userPoints: Int, onRedeem: () -> Unit) {
    val canAfford = userPoints >= reward.cost
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(Modifier.weight(1f)) {
                Text(reward.name, fontWeight = FontWeight.Medium)
                reward.description?.takeIf { it.isNotBlank() }?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                }
                Text("💎 ${reward.cost} Gems", style = MaterialTheme.typography.bodySmall,
                    color = if (canAfford) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error)
            }
            Button(onClick = onRedeem, enabled = canAfford) { Text("Claim") }
        }
    }
}

@Composable
private fun RequestRewardDialog(onDismiss: () -> Unit, onSubmit: (String, Int, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var cost by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Request a Reward") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("Reward name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = cost, onValueChange = { cost = it },
                    label = { Text("Cost (Gems)") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = description, onValueChange = { description = it },
                    label = { Text("Description (optional)") }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val c = cost.toIntOrNull() ?: return@TextButton
                if (name.isNotBlank() && c > 0) onSubmit(name, c, description)
            }) { Text("Submit") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
