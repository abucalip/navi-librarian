import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation

// discair-checks: the two M1 checks of docs/MACOS_CLIENT_CONTRACT.md section 9, run against the owner's servers.
// Logins come from environment variables only. Nothing secret is printed: not passwords, tokens, salts or URLs.

let usage = """
usage:
  discair-checks playlists [--write]
      env: DISCAIR_NAVIDROME_URL, DISCAIR_NAVIDROME_USER, DISCAIR_NAVIDROME_PASSWORD
      Reads playlists. With --write it also creates a playlist named "discair-m1-check" with one song,
      reads it back, adds the song again, deletes it and confirms it is gone.
  discair-checks ratelimit --yes
      env: DISCAIR_LIBRARIAN_URL
      Sends up to 10 wrong logins (username "discair-m1-ratelimit-probe") and prints the attempt number at
      which the server answers 429. This locks that client address out of the Librarian login for 15 minutes.
"""

func fail(_ text: String) -> Never {
    FileHandle.standardError.write(Data((text + "\n").utf8))
    exit(2)
}

func env(_ name: String) -> String {
    guard let v = ProcessInfo.processInfo.environment[name], !v.isEmpty else { fail("missing environment variable \(name)\n\n\(usage)") }
    return v
}

func step(_ name: String, _ body: () async throws -> String) async -> Bool {
    do { print("PASS  \(name): \(try await body())"); return true }
    catch let e as DiscairError { print("FAIL  \(name): \(e.summary)"); return false }
    catch { print("FAIL  \(name): unexpected error"); return false }
}

func playlistsCheck(write: Bool) async -> Bool {
    let client: NavidromeClient
    do {
        let url = try AddressPolicy.validate(env("DISCAIR_NAVIDROME_URL"))
        client = try NavidromeClient(baseURL: url, credential: Credential(username: env("DISCAIR_NAVIDROME_USER"), password: env("DISCAIR_NAVIDROME_PASSWORD")))
    } catch { fail("the Navidrome address was rejected by the transport rules") }

    var ok = await step("ping") { try await client.ping(); return "ok" }
    ok = await step("getPlaylists (read)") { "\(try await client.playlists().count) playlists" } && ok
    guard write else { print("Read-only run. Add --write to test create, update and delete."); return ok }

    var songID: String?
    ok = await step("pick a song") {
        if let album = try await client.albumList(.newest, size: 1).first {
            songID = try await client.album(id: album.id).songs.first?.id
        }
        guard songID != nil else { throw DiscairError.server(status: 200, message: "library is empty") }
        return "found"
    } && ok
    guard let song = songID else { return false }

    var created: String?
    ok = await step("createPlaylist (write)") {
        let p = try await client.createPlaylist(name: "discair-m1-check", songIDs: [song]); created = p.id
        return "created"
    } && ok
    guard let id = created else { return false }
    ok = await step("getPlaylist (read back)") { "\(try await client.playlistSongIDs(id: id).count) songs" } && ok
    ok = await step("updatePlaylist (add song)") {
        try await client.addToPlaylist(id: id, songIDs: [song])
        return "\(try await client.playlistSongIDs(id: id).count) songs after"
    } && ok
    ok = await step("deletePlaylist (write)") { try await client.deletePlaylist(id: id); return "deleted" } && ok
    ok = await step("playlist is gone") {
        guard try await !client.playlists().contains(where: { $0.id == id }) else { throw DiscairError.server(status: 200, message: "still listed") }
        return "confirmed"
    } && ok
    return ok
}

func rateLimitCheck() async -> Bool {
    let url: URL
    do { url = try AddressPolicy.validate(env("DISCAIR_LIBRARIAN_URL")) } catch { fail("the Librarian address was rejected by the transport rules") }
    let bad = Credential(username: "discair-m1-ratelimit-probe", password: "wrong-" + UUID().uuidString)
    guard let client = try? LibrarianClient(baseURL: url, credential: bad) else { fail("could not build the client") }
    for attempt in 1...10 {
        do {
            try await client.login()
            print("attempt \(attempt): unexpectedly accepted"); return false
        } catch DiscairError.unauthorised {
            print("attempt \(attempt): refused (401), as expected")
        } catch DiscairError.tooManyAttempts {
            print("attempt \(attempt): 429 too many attempts. The server limit is reached after \(attempt - 1) attempts from this address.")
            return true
        } catch let e as DiscairError {
            print("attempt \(attempt): \(e.summary)"); return false
        } catch { print("attempt \(attempt): unexpected error"); return false }
    }
    print("No 429 within 10 attempts.")
    return false
}

let args = Array(CommandLine.arguments.dropFirst())
switch args.first {
case "playlists": exit(await playlistsCheck(write: args.contains("--write")) ? 0 : 1)
case "ratelimit":
    guard args.contains("--yes") else { fail("this locks your login out for 15 minutes; pass --yes to confirm\n\n\(usage)") }
    exit(await rateLimitCheck() ? 0 : 1)
default: fail(usage)
}
