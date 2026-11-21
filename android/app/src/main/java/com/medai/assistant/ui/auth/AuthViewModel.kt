package com.medai.assistant.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.medai.assistant.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val isSuccess: Boolean = false,
    val infoMessage: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _state = MutableStateFlow(AuthState())
    val state = _state.asStateFlow()

    val isLoggedIn get() = authRepository.isLoggedIn

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _state.value = AuthState(isLoading = true)
            authRepository.login(email.trim(), password)
                .onSuccess {
                    _state.value = AuthState(isSuccess = true)
                }
                .onFailure {
                    _state.value = AuthState(error = it.message ?: "Login failed. Please check credentials.")
                }
        }
    }

    fun register(email: String, password: String, displayName: String) {
        viewModelScope.launch {
            _state.value = AuthState(isLoading = true)
            authRepository.register(email.trim(), password, displayName.trim())
                .onSuccess {
                    _state.value = AuthState(
                        isSuccess = true,
                        infoMessage = "Account created! Please verify your email before logging in."
                    )
                }
                .onFailure {
                    _state.value = AuthState(error = it.message ?: "Registration failed.")
                }
        }
    }

    fun sendPasswordReset(email: String) {
        viewModelScope.launch {
            _state.value = AuthState(isLoading = true)
            authRepository.sendPasswordReset(email.trim())
                .onSuccess {
                    _state.value = AuthState(
                        isSuccess = true,
                        infoMessage = "Password reset email sent. Please check your inbox."
                    )
                }
                .onFailure {
                    _state.value = AuthState(error = it.message ?: "Failed to send reset email.")
                }
        }
    }

    fun clearState() {
        _state.value = AuthState()
    }

    fun logout() {
        authRepository.logout()
        clearState()
    }
}
