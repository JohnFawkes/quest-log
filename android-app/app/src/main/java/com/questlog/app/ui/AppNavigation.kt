package com.questlog.app.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.questlog.app.data.AuthPreferences
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.ui.screens.*
import com.questlog.app.ui.screens.admin.AdminScreen
import com.questlog.app.viewmodel.*

private data class NavItem(val route: String, val label: String, val icon: ImageVector)

@Composable
fun AppNavigation(authVm: AuthViewModel, prefs: AuthPreferences) {
    val authState by authVm.state.collectAsState()

    when (val state = authState) {
        is AuthState.Loading -> LoadingScreen()
        is AuthState.LoggedOut, is AuthState.Error -> LoginScreen(authVm)
        is AuthState.LoggedIn -> {
            val repo = remember(state.serverUrl) { QuestLogRepository(state.serverUrl) }

            val dashVm = remember(repo, state.token) { DashboardViewModel(repo, state.token) }
            val rewardsVm = remember(repo, state.token) { RewardsViewModel(repo, state.token) }
            val historyVm = remember(repo, state.token) { HistoryViewModel(repo, state.token) }
            val adminVm = remember(repo, state.token) {
                if (state.user.isAdmin) AdminViewModel(repo, state.token) else null
            }

            val navController = rememberNavController()
            val backStack by navController.currentBackStackEntryAsState()
            val currentRoute = backStack?.destination?.route

            val navItems = buildList {
                add(NavItem("dashboard", "Quests", Icons.Default.Home))
                add(NavItem("rewards", "Rewards", Icons.Default.Star))
                add(NavItem("history", "History", Icons.Default.History))
                add(NavItem("settings", "Settings", Icons.Default.Settings))
                if (state.user.isAdmin) add(NavItem("admin", "Guild Hall", Icons.Default.Shield))
            }

            Scaffold(
                bottomBar = {
                    NavigationBar {
                        navItems.forEach { item ->
                            NavigationBarItem(
                                selected = currentRoute == item.route,
                                onClick = {
                                    navController.navigate(item.route) {
                                        popUpTo(navController.graph.startDestinationId) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                },
                                icon = { Icon(item.icon, item.label) },
                                label = { Text(item.label) },
                            )
                        }
                    }
                },
            ) { _ ->
                NavHost(navController, startDestination = "dashboard") {
                    composable("dashboard") {
                        DashboardScreen(vm = dashVm, serverUrl = state.serverUrl)
                    }
                    composable("rewards") {
                        RewardsScreen(vm = rewardsVm)
                    }
                    composable("history") {
                        HistoryScreen(vm = historyVm, serverUrl = state.serverUrl)
                    }
                    composable("settings") {
                        SettingsScreen(
                            user = state.user, token = state.token,
                            repo = repo, authVm = authVm,
                        )
                    }
                    if (adminVm != null) {
                        composable("admin") {
                            AdminScreen(vm = adminVm, serverUrl = state.serverUrl)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LoadingScreen() {
    androidx.compose.foundation.layout.Box(
        modifier = androidx.compose.ui.Modifier.fillMaxSize(),
        contentAlignment = androidx.compose.ui.Alignment.Center,
    ) { CircularProgressIndicator() }
}
