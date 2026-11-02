package app.discair.ui.common

import android.graphics.Color
import android.os.Build
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.window.DialogWindowProvider
import androidx.core.view.WindowCompat

/**
 * Call from inside a bottom sheet's content. A sheet is its own window, so it does not inherit the
 * activity's transparent navigation bar: the system paints a light band under it. This makes the bar
 * transparent with light icons, so the sheet's own color shows through.
 */
@Composable
fun TransparentNavigationBar() {
    val window = (LocalView.current.parent as? DialogWindowProvider)?.window
    SideEffect {
        window ?: return@SideEffect
        window.navigationBarColor = Color.TRANSPARENT
        if (Build.VERSION.SDK_INT >= 29) window.isNavigationBarContrastEnforced = false
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightNavigationBars = false
    }
}
