package com.medai.assistant.data.repository

import com.medai.assistant.data.api.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val api: MedAiApi
) {
    suspend fun getConversations(): Result<List<ConversationSummary>> = runCatching {
        api.getConversations()
    }

    suspend fun createConversation(title: String = "New Conversation"): Result<ConversationSummary> = runCatching {
        api.createConversation(CreateConversationRequest(title = title))
    }

    suspend fun getConversation(id: String): Result<ConversationDetail> = runCatching {
        api.getConversation(id)
    }

    suspend fun deleteConversation(id: String): Result<Unit> = runCatching {
        api.deleteConversation(id)
    }

    suspend fun sendMessage(conversationId: String, text: String): Result<MessageResponse> = runCatching {
        api.sendMessage(conversationId, SendMessageRequest(text = text))
    }
}
