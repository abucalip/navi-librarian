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

/**
 * Call from inside a full-screen dialog (decorFitsSystemWindows = false). Both system bars are transparent with light icons (dark icons when [lightBars], for a light page), no dim sits
 * over the page and the page may run under a display cutout, so the page's own background reaches every edge.
 */
@Composable
fun TransparentSystemBars(lightBars: Boolean = false) {
    val window = (LocalView.current.parent as? DialogWindowProvider)?.window
    SideEffect {
        window ?: return@SideEffect
        window.statusBarColor = Color.TRANSPARENT
        window.navigationBarColor = Color.TRANSPARENT
        window.setDimAmount(0f)
        if (Build.VERSION.SDK_INT >= 28) window.attributes = window.attributes.also { it.layoutInDisplayCutoutMode = android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES }
        if (Build.VERSION.SDK_INT >= 29) window.isNavigationBarContrastEnforced = false
        val controller = WindowCompat.getInsetsController(window, window.decorView)
        controller.isAppearanceLightStatusBars = lightBars
        controller.isAppearanceLightNavigationBars = lightBars
    }
}
