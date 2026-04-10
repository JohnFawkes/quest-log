package com.questlog.app.ui.screens.admin

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.questlog.app.data.api.AppSettings
import com.questlog.app.data.api.UpdateAdminSettingsBody
import com.questlog.app.viewmodel.AdminViewModel

@Composable
fun AdminSettingsTab(vm: AdminViewModel, settings: AppSettings?) {
    var appriseUrls by remember(settings) { mutableStateOf(settings?.appriseUrls ?: "") }
    var discordUrl by remember(settings) { mutableStateOf(settings?.discordWebhookUrl ?: "") }
    var iconUrl by remember(settings) { mutableStateOf(settings?.notificationIconUrl ?: "") }
    var weekStart by remember(settings) { mutableStateOf(settings?.weekStartDay ?: "0") }
    var retention by remember(settings) { mutableStateOf(settings?.approvedImageRetentionDays ?: "0") }

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Notification Settings", style = MaterialTheme.typography.titleSmall)
        OutlinedTextField(value = appriseUrls, onValueChange = { appriseUrls = it },
            label = { Text("Apprise URLs (comma-separated)") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = discordUrl, onValueChange = { discordUrl = it },
            label = { Text("Discord Webhook URL") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = iconUrl, onValueChange = { iconUrl = it },
            label = { Text("Notification Icon URL") }, singleLine = true, modifier = Modifier.fillMaxWidth())

        Divider()
        Text("General Settings", style = MaterialTheme.typography.titleSmall)

        Text("Week Start Day", style = MaterialTheme.typography.labelMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = weekStart == "0", onClick = { weekStart = "0" }, label = { Text("Monday") })
            FilterChip(selected = weekStart == "6", onClick = { weekStart = "6" }, label = { Text("Sunday") })
        }

        OutlinedTextField(value = retention, onValueChange = { retention = it },
            label = { Text("Image retention (days, 0 = keep forever)") },
            singleLine = true, modifier = Modifier.fillMaxWidth())

        Button(
            onClick = {
                vm.saveSettings(UpdateAdminSettingsBody(
                    appriseUrls = appriseUrls,
                    discordWebhookUrl = discordUrl,
                    notificationIconUrl = iconUrl,
                    weekStartDay = weekStart,
                    approvedImageRetentionDays = retention,
                ))
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Save Settings") }
    }
}
