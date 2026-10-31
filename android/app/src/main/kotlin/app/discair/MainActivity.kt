package app.discair

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import app.discair.ui.DiscairApp
import app.discair.ui.theme.DiscairTheme

class MainActivity : ComponentActivity() {
    private val model: AppViewModel by viewModels { AppViewModelFactory(application) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        setContent {
            val state by model.state.collectAsState()
            DiscairTheme { DiscairApp(state, model) }
        }
    }
}
