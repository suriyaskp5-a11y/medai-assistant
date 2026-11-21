package com.medai.assistant.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.medai.assistant.data.api.ConversationSummary
import com.medai.assistant.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HistoryUiState(
    val conversations: List<ConversationSummary> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val chatRepository: ChatRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState = _uiState.asStateFlow()

    init {
        loadConversations()
    }

    fun loadConversations() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            chatRepository.getConversations()
                .onSuccess { convs ->
                    _uiState.update { it.copy(conversations = convs, isLoading = false) }
                }
                .onFailure {
                    _uiState.update { it.copy(isLoading = false, error = "Failed to load history") }
                }
        }
    }

    fun deleteConversation(id: String) {
        viewModelScope.launch {
            chatRepository.deleteConversation(id)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(conversations = state.conversations.filter { it.id != id })
                    }
                }
                .onFailure {
                    _uiState.update { it.copy(error = "Failed to delete conversation") }
                }
        }
    }

    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }
}
