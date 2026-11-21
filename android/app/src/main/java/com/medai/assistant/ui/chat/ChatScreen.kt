package com.medai.assistant.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    conversationId: String? = null,
    onNavigateToHistory: () -> Unit,
    onLogout: () -> Unit,
    viewModel: ChatViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsState()
    var inputText by remember { mutableStateOf("") }
    var showMenu by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

    LaunchedEffect(conversationId) {
        viewModel.initializeConversation(conversationId)
    }

    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("MedAI Assistant", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text(
                            "Medical Education (Tamil & English)",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.startNewConversation() }) {
                        Icon(Icons.Default.Add, contentDescription = "New Chat")
                    }
                    IconButton(onClick = onNavigateToHistory) {
                        Icon(Icons.Default.History, contentDescription = "History")
                    }
                    Box {
                        IconButton(onClick = { showMenu = true }) {
                            Icon(Icons.Default.MoreVert, contentDescription = "Menu")
                        }
                        DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Stop Audio") },
                                onClick = {
                                    showMenu = false
                                    viewModel.stopSpeaking()
                                }
                            )
                            DropdownMenuItem(
                                text = { Text("Sign Out") },
                                onClick = {
                                    showMenu = false
                                    onLogout()
                                }
                            )
                        }
                    }
                }
            )
        },
        bottomBar = {
            Column(modifier = Modifier.fillMaxWidth().navigationBarsPadding()) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "⚕️ For educational use only. Not for diagnosis or personal treatment.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                    )
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = { Text("Ask in Tamil or English...") },
                        modifier = Modifier.weight(1f),
                        maxLines = 4
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            if (inputText.isNotBlank()) {
                                viewModel.sendMessage(inputText)
                                inputText = ""
                            }
                        },
                        enabled = inputText.isNotBlank() && !state.isLoading
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Send",
                            tint = if (inputText.isNotBlank()) MaterialTheme.colorScheme.primary else Color.Gray
                        )
                    }
                }
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (state.messages.isEmpty() && !state.isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize().padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "🩺 Welcome to MedAI Assistant",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Ask any medical concept in Tamil or English.\nExamples:\n• இரத்த அழுத்தம் என்றால் என்ன?\n• Explain the conduction system of the heart\n• Mechanism of action of Metformin",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.messages) { message ->
                        MessageBubble(
                            message = message,
                            onSpeakEn = { text -> viewModel.speakEnglish(text) },
                            onSpeakTa = { text -> viewModel.speakTamil(text) },
                            onStopSpeak = { viewModel.stopSpeaking() }
                        )
                    }
                }
            }

            if (state.error != null) {
                Snackbar(
                    action = {
                        TextButton(onClick = { viewModel.clearError() }) {
                            Text("Dismiss", color = Color.White)
                        }
                    },
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp)
                ) {
                    Text(state.error ?: "")
                }
            }
        }
    }
}

@Composable
fun MessageBubble(
    message: ChatMessage,
    onSpeakEn: (String) -> Unit,
    onSpeakTa: (String) -> Unit,
    onStopSpeak: () -> Unit
) {
    if (message.isUser) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End
        ) {
            Box(
                modifier = Modifier
                    .widthIn(max = 300.dp)
                    .clip(RoundedCornerShape(16.dp, 16.dp, 2.dp, 16.dp))
                    .background(MaterialTheme.colorScheme.primary)
                    .padding(12.dp)
            ) {
                Text(
                    text = message.userText,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontSize = 15.sp
                )
            }
        }
    } else {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Start
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                ),
                shape = RoundedCornerShape(16.dp, 16.dp, 16.dp, 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    if (message.isLoading) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(8.dp)
                        ) {
                            CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.width(12.dp))
                            Text("Analyzing medical concept...", fontSize = 14.sp)
                        }
                    } else if (message.outOfScope) {
                        Text(
                            text = "⚠️ " + (message.englishAnswer ?: "This assistant is only for medical education and medical-related questions."),
                            color = MaterialTheme.colorScheme.error,
                            fontWeight = FontWeight.Medium
                        )
                    } else {
                        if (!message.englishTranslation.isNullOrBlank()) {
                            Text(
                                text = "🌐 English Query: \"${message.englishTranslation}\"",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                        }

                        // English Answer Section
                        Text(
                            text = "🇬🇧 English Explanation",
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 14.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = message.englishAnswer ?: "",
                            style = MaterialTheme.typography.bodyMedium,
                            lineHeight = 20.sp
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // Tamil Explanation Section
                        Text(
                            text = "🇮🇳 தமிழ் விளக்கம்",
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.secondary,
                            fontSize = 14.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = message.tamilExplanation ?: "",
                            style = MaterialTheme.typography.bodyMedium,
                            lineHeight = 22.sp
                        )

                        // Key terms
                        if (message.keyTerms.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(12.dp))
                            Text("📌 Key Terms:", fontWeight = FontWeight.SemiBold, fontSize = 12.sp)
                            message.keyTerms.forEach { (term, tamil) ->
                                Text("• $term — $tamil", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }

                        // Safety note if present
                        if (!message.safetyNote.isNullOrBlank()) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Card(
                                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF9C4))
                            ) {
                                Text(
                                    text = "⚠️ " + message.safetyNote,
                                    fontSize = 12.sp,
                                    color = Color(0xFF5D4037),
                                    modifier = Modifier.padding(8.dp)
                                )
                            }
                        }

                        // Audio Controls
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            FilledTonalButton(
                                onClick = { message.englishAnswer?.let { onSpeakEn(it) } },
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Icon(Icons.Default.VolumeUp, contentDescription = "Play English", modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Play EN", fontSize = 12.sp)
                            }

                            FilledTonalButton(
                                onClick = { message.tamilExplanation?.let { onSpeakTa(it) } },
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Icon(Icons.Default.VolumeUp, contentDescription = "Play Tamil", modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Play TA", fontSize = 12.sp)
                            }

                            IconButton(onClick = onStopSpeak) {
                                Icon(Icons.Default.VolumeOff, contentDescription = "Stop Audio", tint = Color.Gray)
                            }
                        }
                    }
                }
            }
        }
    }
}
