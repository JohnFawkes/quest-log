package com.questlog.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.questlog.app.data.AuthPreferences
import com.questlog.app.ui.AppNavigation
import com.questlog.app.ui.theme.QuestLogTheme
import com.questlog.app.viewmodel.AuthViewModel

class MainActivity : ComponentActivity() {

    private lateinit var prefs: AuthPreferences
    private lateinit var authVm: AuthViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        prefs = AuthPreferences(applicationContext)
        authVm = ViewModelProvider(this, object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                AuthViewModel(prefs) as T
        })[AuthViewModel::class.java]

        setContent {
            QuestLogTheme {
                AppNavigation(authVm = authVm, prefs = prefs)
            }
        }
    }
}
