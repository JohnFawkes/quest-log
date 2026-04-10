package com.questlog.app.ui.screens.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.questlog.app.data.api.User
import com.questlog.app.viewmodel.AdminViewModel

@Composable
fun AdminUsersTab(vm: AdminViewModel, users: List<User>) {
    val state by vm.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    if (showCreateDialog) {
        CreateUserDialog(
            onDismiss = { showCreateDialog = false },
            onConfirm = { email, name, password ->
                vm.createUser(email, name, password)
                showCreateDialog = false
            },
        )
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Default.Add, "Create user")
            }
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item { Spacer(Modifier.height(8.dp)) }
            items(state.users) { user ->
                UserAdminCard(user = user, vm = vm)
            }
            item { Spacer(Modifier.height(72.dp)) }
        }
    }
}

@Composable
private fun UserAdminCard(user: User, vm: AdminViewModel) {
    var showMenu by remember { mutableStateOf(false) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    var showGemDialog by remember { mutableStateOf(false) }
    var showResetDialog by remember { mutableStateOf(false) }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("Remove Adventurer?") },
            text = { Text("Delete ${user.name}? All their quest history will be removed.") },
            confirmButton = {
                TextButton(onClick = { vm.deleteUser(user.id); showDeleteConfirm = false },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { showDeleteConfirm = false }) { Text("Cancel") } },
        )
    }
    if (showGemDialog) {
        AdjustAmountDialog(
            title = "Adjust Gems for ${user.name}",
            onDismiss = { showGemDialog = false },
            onConfirm = { amount -> vm.adjustGems(user.id, amount); showGemDialog = false },
        )
    }
    if (showResetDialog) {
        ResetPasswordDialog(
            name = user.name,
            onDismiss = { showResetDialog = false },
            onConfirm = { pw -> vm.resetPassword(user.id, pw); showResetDialog = false },
        )
    }

    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(user.name, fontWeight = FontWeight.Medium)
                    if (user.isAdmin) Badge { Text("GM") }
                }
                Text(user.email, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                Text("💎 ${user.points}  🪙 ${user.coins}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.secondary)
            }
            Box {
                IconButton(onClick = { showMenu = true }) {
                    Icon(Icons.Default.MoreVert, "Actions")
                }
                DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                    DropdownMenuItem(text = { Text("Adjust Gems") }, onClick = { showMenu = false; showGemDialog = true })
                    DropdownMenuItem(text = { Text("Reset Password") }, onClick = { showMenu = false; showResetDialog = true })
                    if (!user.isAdmin) {
                        DropdownMenuItem(text = { Text("Promote to Guild Master") },
                            onClick = { showMenu = false; vm.promoteUser(user.id) })
                    }
                    DropdownMenuItem(
                        text = { Text("Remove", color = MaterialTheme.colorScheme.error) },
                        onClick = { showMenu = false; showDeleteConfirm = true },
                        leadingIcon = { Icon(Icons.Default.Delete, null, tint = MaterialTheme.colorScheme.error) },
                    )
                }
            }
        }
    }
}

@Composable
private fun CreateUserDialog(onDismiss: () -> Unit, onConfirm: (String, String, String) -> Unit) {
    var email by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Recruit Adventurer") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = email, onValueChange = { email = it },
                    label = { Text("Email") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = password, onValueChange = { password = it },
                    label = { Text("Password") }, singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(onClick = {
                if (email.isNotBlank() && name.isNotBlank() && password.isNotBlank())
                    onConfirm(email, name, password)
            }) { Text("Recruit") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun AdjustAmountDialog(title: String, onDismiss: () -> Unit, onConfirm: (Int) -> Unit) {
    var amount by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(value = amount, onValueChange = { amount = it },
                label = { Text("Amount (negative to deduct)") }, singleLine = true,
                modifier = Modifier.fillMaxWidth())
        },
        confirmButton = {
            TextButton(onClick = { amount.toIntOrNull()?.let { onConfirm(it) } }) { Text("Apply") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun ResetPasswordDialog(name: String, onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    var password by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Reset password for $name") },
        text = {
            OutlinedTextField(value = password, onValueChange = { password = it },
                label = { Text("New password") }, singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth())
        },
        confirmButton = {
            TextButton(onClick = { if (password.isNotBlank()) onConfirm(password) }) { Text("Reset") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
