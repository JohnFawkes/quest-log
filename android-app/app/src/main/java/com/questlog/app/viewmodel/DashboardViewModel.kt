package com.questlog.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.TodayHabitEntry
import com.questlog.app.data.api.UpcomingHabitEntry
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.io.File

data class DashboardUiState(
    val loading: Boolean = true,
    val todayHabits: List<TodayHabitEntry> = emptyList(),
    val upcomingHabits: List<UpcomingHabitEntry> = emptyList(),
    val error: String? = null,
    val completingHabitId: Int? = null,
    val successMessage: String? = null,
)

class DashboardViewModel(
    private val repo: QuestLogRepository,
    private val token: String,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val today = repo.habitsToday(token)
                val upcoming = repo.habitsUpcoming(token)
                _state.value = _state.value.copy(
                    loading = false,
                    todayHabits = today.body()?.habits ?: emptyList(),
                    upcomingHabits = upcoming.body()?.habits ?: emptyList(),
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun completeHabit(habitId: Int, imageFile: File? = null) {
        _state.value = _state.value.copy(completingHabitId = habitId, successMessage = null)
        viewModelScope.launch {
            try {
                val resp = repo.completeHabit(token, habitId, imageFile)
                if (resp.isSuccessful) {
                    _state.value = _state.value.copy(
                        completingHabitId = null,
                        successMessage = "Quest submitted for review!",
                    )
                    load()
                } else {
                    _state.value = _state.value.copy(
                        completingHabitId = null,
                        error = "Failed to submit quest",
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(completingHabitId = null, error = e.message)
            }
        }
    }

    fun clearMessage() { _state.value = _state.value.copy(successMessage = null, error = null) }
}
