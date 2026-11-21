package com.medai.assistant.data.repository

import com.google.firebase.auth.FirebaseAuth
import com.medai.assistant.data.api.MedAiApi
import com.medai.assistant.data.api.RegisterRequest
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val auth: FirebaseAuth,
    private val api: MedAiApi
) {
    val currentUser get() = auth.currentUser
    val isLoggedIn get() = auth.currentUser != null

    suspend fun register(email: String, password: String, displayName: String): Result<Unit> {
        return try {
            val result = auth.createUserWithEmailAndPassword(email, password).await()
            result.user?.sendEmailVerification()?.await()
            api.register(RegisterRequest(display_name = displayName))
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun login(email: String, password: String): Result<Unit> {
        return try {
            auth.signInWithEmailAndPassword(email, password).await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun sendPasswordReset(email: String): Result<Unit> {
        return try {
            auth.sendPasswordResetEmail(email).await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun logout() = auth.signOut()

    suspend fun getIdToken(): String? {
        return try {
            auth.currentUser?.getIdToken(false)?.await()?.token
        } catch (e: Exception) {
            null
        }
    }
}
