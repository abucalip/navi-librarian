-keepclassmembers class app.discair.** { *** Companion; }
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
# Tink (used by EncryptedSharedPreferences) references compile-time-only annotations.
-dontwarn com.google.errorprone.annotations.**
-dontwarn javax.annotation.**
-dontwarn com.google.crypto.tink.**
