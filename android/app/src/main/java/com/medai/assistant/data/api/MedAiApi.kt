package com.medai.assistant.data.api

import retrofit2.http.*

data class RegisterRequest(
    val display_name: String? = null,
    val preferred_lang: String = "en"
)

data class UserProfile(
    val uid: String,
    val email: String,
    val display_name: String?,
    val preferred_lang: String,
    val created_at: String?
)

data class CreateConversationRequest(
    val title: String = "New Conversation"
)

data class ConversationSummary(
    val id: String,
    val title: String,
    val created_at: String,
    val updated_at: String,
    val last_message_preview: String?
)

data class SendMessageRequest(
    val text: String
)

data class KeyMedicalTerm(
    val term: String,
    val tamil: String
)

data class MessageResponse(
    val message_id: String,
    val conversation_id: String,
    val detected_input_language: String,
    val original_question: String,
    val english_question_translation: String?,
    val english_answer: String,
    val tamil_explanation: String,
    val key_medical_terms: List<KeyMedicalTerm>,
    val safety_note: String?,
    val sources: List<String>,
    val out_of_scope: Boolean,
    val created_at: String
)

data class MessageItem(
    val message_id: String,
    val role: String,
    val original_text: String,
    val english_answer: String?,
    val tamil_explanation: String?,
    val english_question_translation: String?,
    val detected_input_language: String?,
    val key_medical_terms: List<KeyMedicalTerm>?,
    val safety_note: String?,
    val sources: List<String>?,
    val out_of_scope: Boolean?,
    val created_at: String
)

data class ConversationDetail(
    val id: String,
    val title: String,
    val messages: List<MessageItem>
)

interface MedAiApi {
    @POST("api/v1/auth/register")
    suspend fun register(@Body body: RegisterRequest): UserProfile

    @GET("api/v1/users/me")
    suspend fun getMe(): UserProfile

    @GET("api/v1/conversations")
    suspend fun getConversations(): List<ConversationSummary>

    @POST("api/v1/conversations")
    suspend fun createConversation(@Body body: CreateConversationRequest): ConversationSummary

    @GET("api/v1/conversations/{id}")
    suspend fun getConversation(@Path("id") id: String): ConversationDetail

    @DELETE("api/v1/conversations/{id}")
    suspend fun deleteConversation(@Path("id") id: String)

    @POST("api/v1/conversations/{id}/messages")
    suspend fun sendMessage(@Path("id") id: String, @Body body: SendMessageRequest): MessageResponse
}
