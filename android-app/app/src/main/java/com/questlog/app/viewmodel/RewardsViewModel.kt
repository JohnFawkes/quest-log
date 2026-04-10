package com.questlog.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.Reward
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class RewardsUiState(
    val loading: Boolean = true,
    val rewards: List<Reward> = emptyList(),
    val points: Int = 0,
    val error: String? = null,
    val successMessage: String? = null,
)

class RewardsViewModel(
    private val repo: QuestLogRepository,
    private val token: String,
) : ViewModel() {

    private val _state = MutableStateFlow(RewardsUiState())
    val state: StateFlow<RewardsUiState> = _state

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val resp = repo.rewards(token)
                val body = resp.body()
                _state.value = _state.value.copy(
                    loading = false,
                    rewards = body?.rewards ?: emptyList(),
                    points = body?.points ?: 0,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun redeem(rewardId: Int) {
        viewModelScope.launch {
            try {
                val resp = repo.redeemReward(token, rewardId)
                if (resp.isSuccessful) {
                    _state.value = _state.value.copy(
                        points = resp.body()?.points ?: _state.value.points,
                        successMessage = "Reward claimed!",
                    )
                } else {
                    _state.value = _state.value.copy(error = "Not enough Gems or error redeeming")
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun requestReward(name: String, cost: Int, description: String) {
        viewModelScope.launch {
            try {
                val resp = repo.requestReward(token, name, cost, description)
                if (resp.isSuccessful) {
                    _state.value = _state.value.copy(successMessage = "Reward requested!")
                } else {
                    _state.value = _state.value.copy(error = "Failed to request reward")
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun clearMessage() { _state.value = _state.value.copy(successMessage = null, error = null) }
}
