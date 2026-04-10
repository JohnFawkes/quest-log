package com.questlog.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.Completion
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter

data class HistoryUiState(
    val loading: Boolean = true,
    val completions: List<Completion> = emptyList(),
    val date: LocalDate = LocalDate.now(),
    val error: String? = null,
)

class HistoryViewModel(
    private val repo: QuestLogRepository,
    private val token: String,
) : ViewModel() {

    private val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd")

    private val _state = MutableStateFlow(HistoryUiState())
    val state: StateFlow<HistoryUiState> = _state

    init { loadDate(LocalDate.now()) }

    fun loadDate(date: LocalDate) {
        _state.value = _state.value.copy(loading = true, date = date, error = null)
        viewModelScope.launch {
            try {
                val resp = repo.history(token, date.format(fmt))
                _state.value = _state.value.copy(
                    loading = false,
                    completions = resp.body()?.completions ?: emptyList(),
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun previousDay() = loadDate(_state.value.date.minusDays(1))
    fun nextDay() { if (_state.value.date < LocalDate.now()) loadDate(_state.value.date.plusDays(1)) }
}
