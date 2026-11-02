package app.discair

import android.content.res.Configuration
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.toArgb
import app.discair.ui.DiscairApp
import app.discair.ui.theme.DiscairTheme
import app.discair.ui.theme.Palette

class MainActivity : ComponentActivity() {
    private lateinit var container: AppContainer
    private val model: AppViewModel by viewModels { AppViewModelFactory(container) }

    /** Window background and system bar icons follow the theme, so no dark flash shows before the first frame. */
    private fun applyWindow(palette: Palette) {
        window.setBackgroundDrawable(ColorDrawable(palette.ink.toArgb()))
        // Dark bar icons on light themes, light icons on dark ones.
        val bars = if (palette.light) SystemBarStyle.light(Color.TRANSPARENT, Color.TRANSPARENT)
        else SystemBarStyle.dark(Color.TRANSPARENT)
        enableEdgeToEdge(statusBarStyle = bars, navigationBarStyle = bars)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        container = (application as DiscairApplication).container
        val appearance = container.appearance
        val systemDark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        applyWindow(appearance.palette(systemDark))
        setContent {
            val state by model.state.collectAsState()
            val palette = appearance.palette(isSystemInDarkTheme())
            LaunchedEffect(palette) { applyWindow(palette) }
            DiscairTheme(palette, appearance.fonts) { DiscairApp(state, model, container) }
        }
    }
}
