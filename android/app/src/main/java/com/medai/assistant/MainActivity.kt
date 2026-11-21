package com.medai.assistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.medai.assistant.ui.auth.*
import com.medai.assistant.ui.chat.ChatScreen
import com.medai.assistant.ui.history.HistoryScreen
import com.medai.assistant.ui.theme.MedAiTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MedAiTheme {
                MedAiNavGraph()
            }
        }
    }
}

@Composable
fun MedAiNavGraph() {
    val navController = rememberNavController()
    val authViewModel: AuthViewModel = hiltViewModel()

    val startDestination = if (authViewModel.isLoggedIn) "chat" else "login"

    NavHost(navController = navController, startDestination = startDestination) {
        composable("login") {
            LoginScreen(
                onNavigateToRegister = { navController.navigate("register") },
                onNavigateToForgotPassword = { navController.navigate("forgot_password") },
                onLoginSuccess = {
                    navController.navigate("chat") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        composable("register") {
            RegisterScreen(
                onNavigateToLogin = { navController.popBackStack() },
                onRegisterSuccess = {
                    navController.navigate("login") {
                        popUpTo("register") { inclusive = true }
                    }
                }
            )
        }

        composable("forgot_password") {
            ForgotPasswordScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable("chat") {
            ChatScreen(
                conversationId = null,
                onNavigateToHistory = { navController.navigate("history") },
                onLogout = {
                    authViewModel.logout()
                    navController.navigate("login") {
                        popUpTo("chat") { inclusive = true }
                    }
                }
            )
        }

        composable(
            route = "chat/{conversationId}",
            arguments = listOf(navArgument("conversationId") { type = NavType.StringType })
        ) { backStackEntry ->
            val conversationId = backStackEntry.arguments?.getString("conversationId")
            ChatScreen(
                conversationId = conversationId,
                onNavigateToHistory = { navController.navigate("history") },
                onLogout = {
                    authViewModel.logout()
                    navController.navigate("login") {
                        popUpTo("chat") { inclusive = true }
                    }
                }
            )
        }

        composable("history") {
            HistoryScreen(
                onNavigateToConversation = { convId ->
                    navController.navigate("chat/$convId")
                },
                onBack = { navController.popBackStack() }
            )
        }
    }
}
