//! Small platform probes shared by the CLI and the backends.

/// Whether this process holds administrator (Windows) or root (Unix) rights.
///
/// Used to decide which backends may run, and — just as importantly — to refuse
/// Microsoft Store updates while elevated, which silently corrupts their
/// install state.
#[cfg(windows)]
pub fn is_elevated() -> bool {
    use windows::Win32::Foundation::HANDLE;
    use windows::Win32::Security::{
        GetTokenInformation, TokenElevation, TOKEN_ELEVATION, TOKEN_QUERY,
    };
    use windows::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};

    // SAFETY: GetCurrentProcess returns a pseudo-handle that is always valid.
    let mut token: HANDLE = Default::default();
    let ok = unsafe { OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut token) };
    if ok.is_err() {
        return false;
    }

    // SAFETY: token is a valid handle from OpenProcessToken. The buffer is a
    // TOKEN_ELEVATION struct, which is what TokenElevation expects.
    let mut elevation = TOKEN_ELEVATION::default();
    let ok = unsafe {
        GetTokenInformation(
            token,
            TokenElevation,
            Some(&mut elevation as *mut _ as *mut _),
            std::mem::size_of::<TOKEN_ELEVATION>() as u32,
            &mut 0u32,
        )
    };

    // SAFETY: token is a valid handle; CloseHandle on a pseudo-handle is a no-op
    // but we call it for correctness.
    unsafe { _ = windows::Win32::Foundation::CloseHandle(token) };

    ok.is_ok() && elevation.TokenIsElevated != 0
}

#[cfg(not(windows))]
pub fn is_elevated() -> bool {
    // SAFETY: geteuid is always safe to call and cannot fail.
    unsafe { libc_geteuid() == 0 }
}

#[cfg(not(windows))]
extern "C" {
    #[link_name = "geteuid"]
    fn libc_geteuid() -> u32;
}

/// Whether Windows is waiting on a restart to finish servicing itself.
///
/// `RunReport::reboot_required` was plumbed to the CLI renderer and to three
/// GUI components, and never once set to `true` — no code assigned it. Reading
/// the flag off an individual install result would only have covered the
/// backend that did the reading; asking the OS covers every backend, including
/// a winget package whose installer staged a pending file rename.
///
/// These are the three signals Windows itself consults, and the same set
/// `security::posture` already checks:
///
///   * Component Based Servicing left a `RebootPending` key behind
///   * Windows Update left a `RebootRequired` key behind
///   * a pending file rename is queued for the next boot
///
/// Any one of them means "restart to finish". Absent or unreadable is reported
/// as "no", because a spurious restart prompt trains users to ignore them.
#[cfg(windows)]
pub fn reboot_pending() -> bool {
    use windows::core::w;

    hklm_key_exists(w!(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"
    )) || hklm_key_exists(w!(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"
    )) || hklm_value_exists(
        w!(r"SYSTEM\CurrentControlSet\Control\Session Manager"),
        w!("PendingFileRenameOperations"),
    )
}

/// Does this key exist under `HKEY_LOCAL_MACHINE`?
#[cfg(windows)]
fn hklm_key_exists(path: windows::core::PCWSTR) -> bool {
    use windows::Win32::System::Registry::{
        RegCloseKey, RegOpenKeyExW, HKEY, HKEY_LOCAL_MACHINE, KEY_READ,
    };

    let mut key = HKEY::default();
    // SAFETY: `path` is a wide string valid for the call, and `key` is a
    // valid out-param that is closed again whenever the open succeeded.
    let opened = unsafe { RegOpenKeyExW(HKEY_LOCAL_MACHINE, path, None, KEY_READ, &mut key) };
    if opened.is_ok() {
        unsafe { _ = RegCloseKey(key) };
        true
    } else {
        false
    }
}

/// Does this value exist under `HKEY_LOCAL_MACHINE\<path>`?
#[cfg(windows)]
fn hklm_value_exists(path: windows::core::PCWSTR, name: windows::core::PCWSTR) -> bool {
    use windows::Win32::System::Registry::{
        RegCloseKey, RegOpenKeyExW, RegQueryValueExW, HKEY, HKEY_LOCAL_MACHINE, KEY_READ,
    };

    let mut key = HKEY::default();
    // SAFETY: both arguments are wide strings valid for the call; `key` is a
    // valid out-param and is closed on every path that opened it.
    let opened = unsafe { RegOpenKeyExW(HKEY_LOCAL_MACHINE, path, None, KEY_READ, &mut key) };
    if opened.is_err() {
        return false;
    }
    let present = unsafe { RegQueryValueExW(key, name, None, None, None, None) }.is_ok();
    unsafe { _ = RegCloseKey(key) };
    present
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;
    use windows::core::w;

    /// `reboot_pending` returning `false` is only meaningful if the registry
    /// reads underneath it can return `true` at all. Both probes are checked
    /// against keys and values that exist on every Windows install, so a
    /// broken call cannot masquerade as "no restart needed".
    #[test]
    fn the_registry_probes_find_things_that_exist() {
        assert!(hklm_key_exists(w!(
            r"SOFTWARE\Microsoft\Windows\CurrentVersion"
        )));
        assert!(hklm_value_exists(
            w!(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"),
            w!("CurrentBuild"),
        ));
    }

    #[test]
    fn the_registry_probes_reject_things_that_do_not_exist() {
        assert!(!hklm_key_exists(w!(
            r"SOFTWARE\Odysync\DefinitelyNotAKeyThatExists"
        )));
        assert!(!hklm_value_exists(
            w!(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"),
            w!("OdysyncDefinitelyNotAValue"),
        ));
    }

    /// A pending reboot must be reported as a plain boolean, never a panic —
    /// this runs on every developer machine and CI runner, in both states.
    #[test]
    fn reboot_pending_answers_without_panicking() {
        let _ = reboot_pending();
    }
}

/// Non-Windows platforms have no equivalent OS-wide signal.
///
/// A Linux kernel update leaves `/var/run/reboot-required` on Debian and
/// nothing at all elsewhere, and macOS does not expose one. Reporting "no"
/// is honest; guessing per-distribution would be worse than saying nothing.
#[cfg(not(windows))]
pub fn reboot_pending() -> bool {
    false
}

/// A short label for the current OS, used in reports and the UI.
pub fn os_label() -> &'static str {
    if cfg!(windows) {
        "Windows"
    } else if cfg!(target_os = "macos") {
        "macOS"
    } else {
        "Linux"
    }
}
