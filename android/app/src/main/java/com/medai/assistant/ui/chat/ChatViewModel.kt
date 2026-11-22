package com.medai.assistant.ui.chat

import android.content.Context
import android.speech.tts.TextToSpeech
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.medai.assistant.data.api.MessageResponse
import com.medai.assistant.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.util.Locale
import javax.inject.Inject

data class ChatMessage(
    val id: String,
    val isUser: Boolean,
    val userText: String,
    val englishTranslation: String? = null,
    val englishAnswer: String? = null,
    val tamilExplanation: String? = null,
    val keyTerms: List<Pair<String, String>> = emptyList(),
    val safetyNote: String? = null,
    val sources: List<String> = emptyList(),
    val outOfScope: Boolean = false,
    val isLoading: Boolean = false
)

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val conversationId: String? = null,
    val isLoading: Boolean = false,
    val isSpeakingEn: Boolean = false,
    val isSpeakingTa: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val chatRepository: ChatRepository,
    @ApplicationContext private val context: Context
) : ViewModel(), TextToSpeech.OnInitListener {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState = _uiState.asStateFlow()

    private var ttsEn: TextToSpeech? = null
    private var ttsTa: TextToSpeech? = null
    private var ttsEnReady = false
    private var ttsTaReady = false

    init {
        ttsEn = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val result = ttsEn?.setLanguage(Locale.ENGLISH)
                ttsEnReady = (result != TextToSpeech.LANG_MISSING_DATA && result != TextToSpeech.LANG_NOT_SUPPORTED)
            }
        }
        ttsTa = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val tamilLocale = Locale("ta", "IN")
                val result = ttsTa?.setLanguage(tamilLocale)
                ttsTaReady = (result != TextToSpeech.LANG_MISSING_DATA && result != TextToSpeech.LANG_NOT_SUPPORTED)
            }
        }
    }

    override fun onInit(status: Int) {}

    fun initializeConversation(existingId: String? = null) {
        if (!existingId.isNullOrBlank()) {
            loadConversation(existingId)
        } else if (_uiState.value.conversationId == null) {
            startNewConversation()
        }
    }

    fun startNewConversation() {
        stopSpeaking()
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            chatRepository.createConversation()
                .onSuccess { conv ->
                    _uiState.update {
                        it.copy(conversationId = conv.id, messages = emptyList(), isLoading = false)
                    }
                }
                .onFailure {
                    _uiState.update { state ->
                        state.copy(isLoading = false, error = "Failed to start new conversation")
                    }
                }
        }
    }

    fun loadConversation(id: String) {
        stopSpeaking()
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            chatRepository.getConversation(id)
                .onSuccess { conv ->
                    val messages = conv.messages.map { msg ->
                        if (msg.role == "user") {
                            ChatMessage(id = msg.message_id, isUser = true, userText = msg.original_text)
                        } else {
                            ChatMessage(
                                id = msg.message_id,
                                isUser = false,
                                userText = "",
                                englishAnswer = msg.english_answer,
                                tamilExplanation = msg.tamil_explanation,
                                englishTranslation = msg.english_question_translation,
                                keyTerms = msg.key_medical_terms?.map { it.term to it.tamil } ?: emptyList(),
                                safetyNote = msg.safety_note,
                                sources = msg.sources ?: emptyList(),
                                outOfScope = msg.out_of_scope ?: false
                            )
                        }
                    }
                    _uiState.update {
                        it.copy(conversationId = id, messages = messages, isLoading = false)
                    }
                }
                .onFailure {
                    _uiState.update { state ->
                        state.copy(isLoading = false, error = "Failed to load conversation")
                    }
                }
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return

        val convId = _uiState.value.conversationId
        if (convId == null) {
            viewModelScope.launch {
                chatRepository.createConversation().onSuccess { conv ->
                    _uiState.update { it.copy(conversationId = conv.id) }
                    doSendMessage(conv.id, trimmed)
                }
            }
        } else {
            doSendMessage(convId, trimmed)
        }
    }

    private fun doSendMessage(convId: String, text: String) {
        val userMsg = ChatMessage(id = System.currentTimeMillis().toString(), isUser = true, userText = text)
        val loadingMsg = ChatMessage(id = "loading", isUser = false, userText = "", isLoading = true)
        _uiState.update { it.copy(messages = it.messages + userMsg + loadingMsg, error = null) }

        viewModelScope.launch {
            chatRepository.sendMessage(convId, text)
                .onSuccess { response ->
                    val assistantMsg = ChatMessage(
                        id = response.message_id,
                        isUser = false,
                        userText = "",
                        englishTranslation = response.english_question_translation,
                        englishAnswer = response.english_answer,
                        tamilExplanation = response.tamil_explanation,
                        keyTerms = response.key_medical_terms.map { it.term to it.tamil },
                        safetyNote = response.safety_note,
                        sources = response.sources,
                        outOfScope = response.out_of_scope
                    )
                    _uiState.update { state ->
                        state.copy(messages = state.messages.dropLast(1) + assistantMsg)
                    }
                }
                .onFailure { error ->
                    val errorDetail = error.message ?: ""
                    _uiState.update { state ->
                        state.copy(
                            messages = state.messages.dropLast(1),
                            error = when {
                                errorDetail.contains("429") -> "Daily or rate limit reached. Please wait a moment."
                                errorDetail.contains("401") -> "Session expired. Please sign in again."
                                errorDetail.contains("timeout", ignoreCase = true) -> "Server is waking up (Render free tier cold start). Please tap send again!"
                                else -> "Connection error. Please tap send again."
                            }
                        )
                    }
                }
        }
    }

    /**
     * Clean markdown symbols before passing text to TTS.
     * Removes ##, **, *, _, ~, `, bullets, links — so only natural language is spoken.
     */
    private fun cleanForTTS(text: String): String {
        return text
            .replace(Regex("#{1,6}\\s*"), "")           // Remove ## headings
            .replace(Regex("\\*\\*(.*?)\\*\\*"), "$1")  // Remove **bold**
            .replace(Regex("\\*(.*?)\\*"), "$1")         // Remove *italic*
            .replace(Regex("__(.*?)__"), "$1")           // Remove __bold__
            .replace(Regex("_(.*?)_"), "$1")             // Remove _italic_
            .replace(Regex("~~(.*?)~~"), "$1")           // Remove ~~strikethrough~~
            .replace(Regex("`{1,3}[^`]*`{1,3}"), "")    // Remove `code`
            .replace(Regex("\\[([^\\]]+)]\\([^)]+\\)"), "$1") // Remove [links](url)
            .replace(Regex("^[•\\-\\*]\\s+", RegexOption.MULTILINE), "") // Remove bullet - or •
            .replace(Regex("^\\d+\\.\\s+", RegexOption.MULTILINE), "")   // Remove 1. 2. list numbers
            .replace(Regex("[*#_~`]"), "")               // Remove any remaining symbols
            .replace(Regex("\\s{2,}"), " ")              // Collapse multiple spaces
            .replace(Regex("\n{2,}"), ". ")              // Replace double newlines with pause
            .replace("\n", " ")                          // Replace single newlines with space
            .trim()
    }

    fun speakEnglish(text: String) {
        stopSpeaking()
        if (ttsEnReady) {
            _uiState.update { it.copy(isSpeakingEn = true, isSpeakingTa = false) }
            ttsEn?.speak(cleanForTTS(text), TextToSpeech.QUEUE_FLUSH, null, "en_utt")
        } else {
            _uiState.update { it.copy(error = "English TTS not ready on this device.") }
        }
    }

    fun speakTamil(text: String) {
        stopSpeaking()
        if (ttsTaReady) {
            _uiState.update { it.copy(isSpeakingTa = true, isSpeakingEn = false) }
            ttsTa?.speak(cleanForTTS(text), TextToSpeech.QUEUE_FLUSH, null, "ta_utt")
        } else {
            _uiState.update {
                it.copy(error = "Tamil voice pack not found. Enable Google Text-to-Speech Tamil voice in Phone Settings.")
            }
        }
    }

    fun stopSpeaking() {
        ttsEn?.stop()
        ttsTa?.stop()
        _uiState.update { it.copy(isSpeakingEn = false, isSpeakingTa = false) }
    }

    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    override fun onCleared() {
        super.onCleared()
        ttsEn?.shutdown()
        ttsTa?.shutdown()
    }
}
