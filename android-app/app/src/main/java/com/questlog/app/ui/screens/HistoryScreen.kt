package com.questlog.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.questlog.app.data.api.Completion
import com.questlog.app.viewmodel.HistoryViewModel
import java.time.LocalDate
import java.time.format.DateTimeFormatter

@Composable
fun HistoryScreen(vm: HistoryViewModel, serverUrl: String) {
    val state by vm.state.collectAsState()
    val today = remember { LocalDate.now() }
    val displayFmt = remember { DateTimeFormatter.ofPattern("EEE, MMM d") }

    Column(Modifier.fillMaxSize()) {
        // Date navigation bar
        Surface(tonalElevation = 4.dp) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = { vm.previousDay() }) {
                    Icon(Icons.Default.ChevronLeft, "Previous day")
                }
                Text(
                    text = if (state.date == today) "Today" else state.date.format(displayFmt),
                    style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold,
                )
                IconButton(onClick = { vm.nextDay() }, enabled = state.date < today) {
                    Icon(Icons.Default.ChevronRight, "Next day")
                }
            }
        }

        if (state.loading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        } else if (state.completions.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No quest activity on this day.", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item { Spacer(Modifier.height(8.dp)) }
                items(state.completions) { c ->
                    CompletionCard(c, serverUrl)
                }
                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }
}

@Composable
private fun CompletionCard(c: Completion, serverUrl: String) {
    val statusColor = when (c.status) {
        "approved" -> MaterialTheme.colorScheme.secondary
        "pending" -> MaterialTheme.colorScheme.primary
        "penalty" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.error.copy(alpha = 0.7f)
    }
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            c.imageUrl?.let { url ->
                AsyncImage(
                    model = "$serverUrl$url",
                    contentDescription = null,
                    modifier = Modifier.size(64.dp),
                )
            }
            Column(Modifier.weight(1f)) {
                Text(c.habitName, fontWeight = FontWeight.Medium)
                c.userName?.let { Text(it, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) }
                Text(c.status.replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.bodySmall, color = statusColor)
                c.timestamp?.take(16)?.replace("T", " ")?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f))
                }
            }
        }
    }
}
