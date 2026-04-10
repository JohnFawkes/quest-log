package com.questlog.app.ui.screens.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.questlog.app.data.api.Completion
import com.questlog.app.viewmodel.AdminViewModel

// Tab-based admin panel showing: Pending | Habits | Users | Rewards | Settings
@Composable
fun AdminScreen(vm: AdminViewModel, serverUrl: String) {
    val state by vm.state.collectAsState()
    val tabs = listOf("Pending", "Quests", "Adventurers", "Rewards", "Settings")
    var selectedTab by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.successMessage) {
        state.successMessage?.let { snackbarHostState.showSnackbar(it); vm.clearMessage() }
    }
    LaunchedEffect(state.error) {
        state.error?.let { snackbarHostState.showSnackbar("Error: $it"); vm.clearMessage() }
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbarHostState) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(selectedTabIndex = selectedTab, edgePadding = 0.dp) {
                tabs.forEachIndexed { idx, title ->
                    Tab(selected = selectedTab == idx, onClick = { selectedTab = idx },
                        text = {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(title)
                                if (idx == 0 && state.pending.isNotEmpty()) {
                                    Badge { Text(state.pending.size.toString()) }
                                }
                            }
                        })
                }
            }

            if (state.loading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            } else {
                when (selectedTab) {
                    0 -> PendingTab(state.pending, serverUrl, vm)
                    1 -> AdminHabitsTab(vm, state.users)
                    2 -> AdminUsersTab(vm, state.users)
                    3 -> AdminRewardsTab(vm, state.rewards)
                    4 -> AdminSettingsTab(vm, state.settings)
                }
            }
        }
    }
}

@Composable
private fun PendingTab(pending: List<Completion>, serverUrl: String, vm: AdminViewModel) {
    if (pending.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("No pending quests. The realm is at peace! ⚔️",
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
        }
        return
    }
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item { Spacer(Modifier.height(8.dp)) }
        items(pending) { c ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text(c.habitName, fontWeight = FontWeight.Bold)
                            Text(c.userName ?: "Unknown", style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                        }
                        c.timestamp?.take(10)?.let {
                            Text(it, style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f))
                        }
                    }
                    c.imageUrl?.let { url ->
                        AsyncImage(model = "$serverUrl$url", contentDescription = null,
                            modifier = Modifier.fillMaxWidth().height(180.dp))
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { vm.approve(c.id) }, modifier = Modifier.weight(1f)) { Text("✅ Approve") }
                        OutlinedButton(
                            onClick = { vm.reject(c.id) }, modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                        ) { Text("❌ Reject") }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}
