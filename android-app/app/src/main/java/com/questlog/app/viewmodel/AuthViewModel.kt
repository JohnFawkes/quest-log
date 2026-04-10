package com.questlog.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.questlog.app.data.AuthPreferences
import com.questlog.app.data.QuestLogRepository
import com.questlog.app.data.api.User
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

sealed class AuthState {
    object Loading : AuthState()
    object LoggedOut : AuthState()
    data class LoggedIn(val user: User, val token: String, val serverUrl: String) : AuthState()
    data class Error(val message: String) : AuthState()
}

class AuthViewModel(
    private val prefs: AuthPreferences,
) : ViewModel() {

    private val _state = MutableStateFlow<AuthState>(AuthState.Loading)
    val state: StateFlow<AuthState> = _state

    init {
        viewModelScope.launch { restoreSession() }
    }

    private suspend fun restoreSession() {
        val token = prefs.token.first()
        val url = prefs.serverUrl.first()
        if (token.isNullOrBlank() || url.isNullOrBlank()) {
            _state.value = AuthState.LoggedOut
            return
        }
        try {
            val repo = QuestLogRepository(url)
            val resp = repo.me(token)
            if (resp.isSuccessful && resp.body() != null) {
                _state.value = AuthState.LoggedIn(resp.body()!!.user, token, url)
            } else {
                prefs.clear()
                _state.value = AuthState.LoggedOut
            }
        } catch (e: Exception) {
            // Network error — still restore session optimistically
            _state.value = AuthState.LoggedOut
        }
    }

    fun login(serverUrl: String, email: String, password: String) {
        val url = serverUrl.trim().trimEnd('/')
        if (url.isBlank() || email.isBlank() || password.isBlank()) {
            _state.value = AuthState.Error("All fields are required")
            return
        }
        _state.value = AuthState.Loading
        viewModelScope.launch {
            try {
                val repo = QuestLogRepository(url)
                val resp = repo.login(email, password)
                if (resp.isSuccessful && resp.body() != null) {
                    val body = resp.body()!!
                    prefs.save(body.token, url)
                    _state.value = AuthState.LoggedIn(body.user, body.token, url)
                } else {
                    _state.value = AuthState.Error("Invalid credentials")
                }
            } catch (e: Exception) {
                _state.value = AuthState.Error("Cannot reach server: ${e.message}")
            }
        }
    }

    fun logout() {
        val current = _state.value as? AuthState.LoggedIn ?: return
        viewModelScope.launch {
            try {
                QuestLogRepository(current.serverUrl).logout(current.token)
            } catch (_: Exception) {}
            prefs.clear()
            _state.value = AuthState.LoggedOut
        }
    }

    fun clearError() {
        if (_state.value is AuthState.Error) _state.value = AuthState.LoggedOut
    }

    fun updateUser(user: User) {
        val current = _state.value as? AuthState.LoggedIn ?: return
        _state.value = current.copy(user = user)
    }
}
