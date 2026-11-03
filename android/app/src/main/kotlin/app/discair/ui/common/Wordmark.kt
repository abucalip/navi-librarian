package app.discair.ui.common

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import app.discair.R
import app.discair.ui.theme.Ink

/**
 * The Discair wordmark, in the theme's own colours: the letters in the text colour and the two i-dots in the accent
 * (owner request, 2026-11-02). Two layers of one drawable set (traced from static/discair-logo.svg), so every theme
 * gets a wordmark that reads on its header: the letters follow the page text, the dots follow the accent.
 * It is one heading for TalkBack.
 */
@Composable
fun Wordmark(height: Dp, modifier: Modifier = Modifier) {
    Box(modifier.height(height).aspectRatio(1440f / 371f).semantics { contentDescription = "Discair"; heading() }) {
        Icon(painterResource(R.drawable.ic_wordmark_letters), contentDescription = null, tint = Ink.Text, modifier = Modifier.fillMaxSize())
        Icon(painterResource(R.drawable.ic_wordmark_dots), contentDescription = null, tint = Ink.Accent, modifier = Modifier.fillMaxSize())
    }
}
