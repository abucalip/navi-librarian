package app.discair

import app.discair.data.ServerSettings
import app.discair.data.SettingsStore
import app.discair.net.ConnectionFailure
import app.discair.net.UrlProblem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AppViewModelTest {
    private val dispatcher = UnconfinedTestDispatcher()

    private class MemoryStore(var value: ServerSettings = ServerSettings()) : SettingsStore {
        var saves = 0
        override fun load() = value
        override fun save(settings: ServerSettings) { value = settings; saves++ }
        override fun clear() { value = ServerSettings() }
    }

    private class FakeConnector(
        var librarian: Check = Check.Ok,
        var navidrome: Check = Check.Ok,
    ) : Connector {
        var signedOut = false
        var offlineData = false
        override fun hasOfflineData() = offlineData
        override fun networkAvailable() = true
        override fun checkLibrarian(url: String, user: String, password: String) = librarian
        override fun checkNavidrome(url: String, user: String, password: String) = navidrome
        override fun signOut(librarianUrl: String, user: String, password: String) { signedOut = true }
    }

    private val complete = ServerSettings("https://l.ts.net", "u", "pw", "https://n.ts.net", "u", "pw")

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun model(store: SettingsStore, connector: Connector) = AppViewModel(store, connector, dispatcher)

    @Test fun firstLaunchShowsSetup() {
        assertEquals(Screen.Setup, model(MemoryStore(), FakeConnector()).state.value.screen)
    }

    @Test fun savedSettingsSignInOnRestart() {
        val vm = model(MemoryStore(complete), FakeConnector())
        assertEquals(Screen.Home, vm.state.value.screen)
    }

    @Test fun unreachableServerOnRestartShowsUnavailableWithTheReason() {
        val connector = FakeConnector(librarian = Check.Failed(ConnectionFailure.Unreachable))
        val vm = model(MemoryStore(complete), connector)
        assertEquals(Screen.Unavailable, vm.state.value.screen)
        assertEquals(complete, vm.state.value.saved)
        assertEquals(Check.Failed(ConnectionFailure.Unreachable), vm.state.value.librarian)
        assertEquals(Check.Ok, vm.state.value.navidrome)
    }

    @Test fun noConnectionWithSavedCopiesOpensHomeInsteadOfADeadEnd() {
        val connector = FakeConnector(librarian = Check.Failed(ConnectionFailure.Unreachable)).also { it.offlineData = true }
        assertEquals(Screen.Home, model(MemoryStore(complete), connector).state.value.screen)
        connector.librarian = Check.Failed(ConnectionFailure.NoNetwork)
        assertEquals(Screen.Home, model(MemoryStore(complete), connector).state.value.screen)
    }

    @Test fun aRefusalIsNotTreatedAsOfflineEvenWithSavedCopies() {
        val connector = FakeConnector(librarian = Check.Failed(ConnectionFailure.Unauthorised())).also { it.offlineData = true }
        assertEquals(Screen.Unavailable, model(MemoryStore(complete), connector).state.value.screen)
        val server = FakeConnector(librarian = Check.Failed(ConnectionFailure.Server(500))).also { it.offlineData = true }
        assertEquals(Screen.Unavailable, model(MemoryStore(complete), server).state.value.screen)
    }

    @Test fun rejectedCredentialsDuringASessionReturnToSetupWithAReason() {
        val vm = model(MemoryStore(complete), FakeConnector())
        assertEquals(Screen.Home, vm.state.value.screen)
        vm.sessionExpired()
        vm.sessionExpired() // several in-flight calls may report it; the result is the same
        assertEquals(Screen.Setup, vm.state.value.screen)
        assertEquals(complete, vm.state.value.form)
        assertTrue(vm.state.value.notice!!.contains("signed out"))
        vm.connect()
        assertEquals(Screen.Home, vm.state.value.screen)
        assertEquals(null, vm.state.value.notice)
    }

    @Test fun connectStoresSettingsOnlyWhenBothServersPass() {
        val store = MemoryStore()
        val connector = FakeConnector(navidrome = Check.Failed(ConnectionFailure.Unauthorised()))
        val vm = model(store, connector)
        vm.edit { complete.copy(librarianUrl = "l.ts.net", navidromeUrl = "n.ts.net") }
        vm.connect()
        assertEquals(0, store.saves)
        assertEquals(Screen.Setup, vm.state.value.screen)
        connector.navidrome = Check.Ok
        vm.connect()
        assertEquals(1, store.saves)
        assertEquals("https://l.ts.net", store.value.librarianUrl)
        assertEquals(Screen.Home, vm.state.value.screen)
    }

    @Test fun cleartextAddressIsRefusedBeforeAnyNetworkCall() {
        val vm = model(MemoryStore(), FakeConnector())
        vm.edit { complete.copy(librarianUrl = "http://l.ts.net") }
        vm.connect()
        assertEquals(UrlProblem.NotHttps, vm.state.value.librarianUrlProblem)
        assertEquals(Check.Idle, vm.state.value.librarian)
    }

    @Test fun tryAgainRecoversWhenTheServerComesBack() {
        val connector = FakeConnector(librarian = Check.Failed(ConnectionFailure.Unreachable))
        val vm = model(MemoryStore(complete), connector)
        connector.librarian = Check.Ok
        vm.recheck()
        assertEquals(Screen.Home, vm.state.value.screen)
    }

    @Test fun incompleteFormFlagsMissingFieldsWithoutCheckingAnything() {
        val vm = model(MemoryStore(), FakeConnector())
        vm.edit { it.copy(librarianUrl = "l.ts.net") }
        vm.connect()
        assertTrue(vm.state.value.showMissing)
        assertEquals(Screen.Setup, vm.state.value.screen)
        assertEquals(Check.Idle, vm.state.value.librarian)
    }

    @Test fun cancelDropsEditsAndReturnsToTheSavedServers() {
        val vm = model(MemoryStore(complete), FakeConnector())
        vm.editServers()
        vm.edit { it.copy(librarianUrl = "https://typo.ts.net") }
        assertTrue(vm.state.value.canCancelEdit)
        vm.cancelEdit()
        assertEquals(complete, vm.state.value.form)
        assertEquals(Screen.Home, vm.state.value.screen)
    }

    @Test fun cancelIsNotOfferedOnFirstSetup() {
        val vm = model(MemoryStore(), FakeConnector())
        assertFalse(vm.state.value.canCancelEdit)
        vm.cancelEdit()
        assertEquals(Screen.Setup, vm.state.value.screen)
    }

    @Test fun failedEditKeepsTheWorkingSavedSettings() {
        val store = MemoryStore(complete)
        val connector = FakeConnector()
        val vm = model(store, connector)
        vm.editServers()
        connector.navidrome = Check.Failed(ConnectionFailure.Unauthorised())
        vm.edit { it.copy(navidromePassword = "wrong") }
        vm.connect()
        assertEquals(complete, store.value)
        assertEquals(complete, vm.state.value.saved)
        assertEquals(Screen.Setup, vm.state.value.screen)
    }

    @Test fun signOutForgetsEverythingAndTellsTheServer() {
        val store = MemoryStore(complete)
        val connector = FakeConnector()
        val vm = model(store, connector)
        vm.signOut()
        assertTrue(connector.signedOut)
        assertFalse(store.value.isComplete)
        assertEquals(Screen.Setup, vm.state.value.screen)
    }
}
