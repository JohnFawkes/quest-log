package com.questlog.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AdminUiState(
    val loading: Boolean = true,
    val pending: List<Completion> = emptyList(),
    val habits: List<Habit> = emptyList(),
    val users: List<User> = emptyList(),
    val rewards: List<Reward> = emptyList(),
    val settings: AppSettings? = null,
    val error: String? = null,
    val successMessage: String? = null,
)

class AdminViewModel(
    private val repo: QuestLogRepository,
    private val token: String,
) : ViewModel() {

    private val _state = MutableStateFlow(AdminUiState())
    val state: StateFlow<AdminUiState> = _state

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val pending = repo.adminPending(token).body()?.completions ?: emptyList()
                val habits = repo.adminHabits(token).body()?.habits ?: emptyList()
                val users = repo.adminUsers(token).body()?.users ?: emptyList()
                val rewards = repo.adminRewards(token).body()?.rewards ?: emptyList()
                val settings = repo.adminGetSettings(token).body()
                _state.value = _state.value.copy(
                    loading = false, pending = pending, habits = habits,
                    users = users, rewards = rewards, settings = settings,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    // Completions
    fun approve(completionId: Int) = adminAction {
        repo.adminApprove(token, completionId)
        "Quest approved!"
    }

    fun reject(completionId: Int) = adminAction {
        repo.adminReject(token, completionId)
        "Quest rejected."
    }

    // Habits
    fun createHabit(body: CreateHabitBody) = adminAction {
        repo.adminCreateHabit(token, body)
        "Quest created!"
    }

    fun updateHabit(habitId: Int, body: UpdateHabitBody) = adminAction {
        repo.adminUpdateHabit(token, habitId, body)
        "Quest updated."
    }

    fun deleteHabit(habitId: Int) = adminAction {
        repo.adminDeleteHabit(token, habitId)
        "Quest deleted."
    }

    // Users
    fun createUser(email: String, name: String, password: String) = adminAction {
        repo.adminCreateUser(token, email, name, password)
        "Adventurer created!"
    }

    fun deleteUser(userId: Int) = adminAction {
        repo.adminDeleteUser(token, userId)
        "Adventurer removed."
    }

    fun promoteUser(userId: Int) = adminAction {
        repo.adminPromoteUser(token, userId)
        "Adventurer promoted to Guild Master!"
    }

    fun resetPassword(userId: Int, newPassword: String) = adminAction {
        repo.adminResetPassword(token, userId, newPassword)
        "Password reset."
    }

    fun adjustGems(userId: Int, amount: Int) = adminAction {
        repo.adminAdjustGems(token, userId, amount)
        "Gems adjusted."
    }

    fun adjustCoins(userId: Int, amount: Int) = adminAction {
        repo.adminAdjustCoins(token, userId, amount)
        "Coins adjusted."
    }

    // Rewards
    fun approveReward(rewardId: Int) = adminAction {
        repo.adminApproveReward(token, rewardId)
        "Reward approved!"
    }

    fun deleteReward(rewardId: Int) = adminAction {
        repo.adminDeleteReward(token, rewardId)
        "Reward deleted."
    }

    fun createReward(name: String, cost: Int, description: String, icon: String) = adminAction {
        repo.adminCreateReward(token, name, cost, description, icon)
        "Reward created!"
    }

    // Settings
    fun saveSettings(body: UpdateAdminSettingsBody) = adminAction {
        repo.adminUpdateSettings(token, body)
        "Settings saved."
    }

    fun clearMessage() { _state.value = _state.value.copy(successMessage = null, error = null) }

    private fun adminAction(block: suspend () -> String) {
        viewModelScope.launch {
            try {
                val msg = block()
                _state.value = _state.value.copy(successMessage = msg)
                load()
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
