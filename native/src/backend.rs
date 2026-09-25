use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::str::FromStr;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Emitter, Manager};

pub struct BackendProcess(pub Mutex<Option<Child>>);

const BACKEND_NAME: &str = "arxiv-mcp-backend.exe";
const BACKEND_PORT: u16 = 10770;
const BACKEND_TAG: &str = "arxiv-mcp-backend-x86_64-pc-windows-msvc.exe";
const ENV_PORT: &str = "ARXIV_MCP_PORT";
const ENV_HOST: &str = "ARXIV_MCP_HOST";
const ENV_TAURI: &str = "ARXIV_TAURI";
const HEALTH_PATH: &str = "/api/health";

fn dev_backend_path() -> Option<PathBuf> {
    if !cfg!(debug_assertions) { return None; }
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries").join(BACKEND_TAG);
    path.exists().then_some(path)
}

fn log_line(app: &AppHandle, message: &str) {
    eprintln!("[backend] {message}");
    if let Ok(dir) = app.path().app_log_dir() {
        let _ = fs::create_dir_all(&dir);
        let log_path = dir.join("backend-spawn.log");
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
            let _ = writeln!(file, "{message}");
        }
    }
}

fn resolve_bundled_backend(app: &AppHandle) -> Result<PathBuf, String> {
    let mut tried = Vec::new();
    if let Ok(path) = app.path().resolve(BACKEND_NAME, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    let resources_path = format!("resources/{BACKEND_NAME}");
    if let Ok(path) = app.path().resolve(&resources_path, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    if let Ok(dir) = app.path().executable_dir() {
        let path = dir.join("resources").join(BACKEND_NAME);
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    Err(format!("bundled backend missing (tried: {})", tried.join("; ")))
}

pub fn materialize_backend(app: &AppHandle) -> Result<PathBuf, String> {
    if let Some(dev_path) = dev_backend_path() {
        log_line(app, &format!("using dev backend: {}", dev_path.display()));
        return Ok(dev_path);
    }
    let bundled = resolve_bundled_backend(app)?;
    log_line(app, &format!("using bundled backend: {}", bundled.display()));
    // Strip Windows extended-length prefix
    let s = bundled.to_string_lossy().to_string();
    let clean = s.strip_prefix("\\\\?\\").map(PathBuf::from).unwrap_or(bundled.clone());
    Ok(clean)
}

/// True if something on 127.0.0.1:port is not just bound but actually
/// answering HTTP requests - i.e. a live, healthy backend, not a zombie
/// that crashed mid-request and left the port bound with nothing behind it.
/// See advanced-memory-mcp/src-tauri/src/backend.rs for the full rationale
/// (same fix applied fleet-wide against a copied Tauri template that force-
/// killed whatever held its backend port on every launch).
fn port_holder_is_responsive(port: u16) -> bool {
    let addr = match ("127.0.0.1", port).to_socket_addrs() {
        Ok(mut addrs) => match addrs.next() {
            Some(addr) => addr,
            None => return false,
        },
        Err(_) => return false,
    };
    let mut stream = match TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(1500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
    let request = format!("GET {HEALTH_PATH} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut buf = [0u8; 64];
    let n = match stream.read(&mut buf) {
        Ok(n) if n > 0 => n,
        _ => return false,
    };
    String::from_utf8_lossy(&buf[..n]).split_whitespace().nth(1) == Some("200")
}

fn free_port(port: u16) {
    #[cfg(windows)]
    {
        let script = format!(
            "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue \
            | ForEach-Object {{ taskkill /F /PID `$_.OwningProcess /T 2>$null }}"
        );
        let _ = Command::new("powershell.exe")
            .args(["-NoProfile", "-Command", &script])
            .stdout(Stdio::null()).stderr(Stdio::null())
            .status();
        thread::sleep(Duration::from_millis(500));
    }
}

fn stop_managed_child(state: &BackendProcess) {
    if let Some(mut child) = state.0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

pub fn spawn_backend(app: AppHandle, state: &BackendProcess) -> Result<String, String> {
    stop_managed_child(state);

    // Attach to an already-healthy backend instead of killing it. A
    // genuinely dead/hung holder still gets force-killed below, unchanged.
    if port_holder_is_responsive(BACKEND_PORT) {
        log_line(
            &app,
            &format!("port {BACKEND_PORT} already serving and responsive - attaching instead of spawning a second backend"),
        );
        return Ok(format!("Attached to existing backend on port {BACKEND_PORT}"));
    }

    free_port(BACKEND_PORT);

    let backend_path = materialize_backend(&app)?;
    let workdir = app.path().executable_dir().ok().unwrap_or_default();

    log_line(&app, &format!("spawning {} (cwd {}) on port {}", backend_path.display(), workdir.display(), BACKEND_PORT));

    let mut command = Command::new(&backend_path);
    command
        .current_dir(&workdir)
        .env(ENV_PORT, BACKEND_PORT.to_string())
        .env(ENV_HOST, "127.0.0.1")
        .env(ENV_TAURI, "1")
        .stdout(Stdio::null()); // stdout to NUL — pipe buffer hangs the backend

    // Redirect stderr to a file so we can see crash tracebacks
    let stderr_path = app.path().app_log_dir().ok().map(|d| {
        let _ = fs::create_dir_all(&d);
        d.join("backend-stderr.log")
    });
    if let Some(ref p) = stderr_path {
        if let Ok(f) = File::create(p) {
            command.stderr(f);
        } else {
            command.stderr(Stdio::null());
        }
    } else {
        command.stderr(Stdio::null());
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command
        .spawn()
        .map_err(|e| format!("Failed to spawn {}: {e}", backend_path.display()))?;

    // Store child in managed state
    state.0.lock().unwrap().replace(child);

    // Poll backend TCP port to confirm it is actually listening (up to 3 min)
    let addr = SocketAddr::from_str(&format!("127.0.0.1:{BACKEND_PORT}")).unwrap();
    let app_health = app.clone();
    thread::spawn(move || {
        for attempt in 0..90 {
            thread::sleep(Duration::from_secs(2));
            match TcpStream::connect_timeout(&addr, Duration::from_secs(2)) {
                Ok(_) => {
                    log_line(&app_health, &format!("Backend health check PASSED on port {BACKEND_PORT} (attempt {})", attempt + 1));
                    let _ = app_health.emit("backend-status", "ready");
                    return;
                }
                Err(e) => {
                    log_line(&app_health, &format!("Backend health check: {e} (attempt {})", attempt + 1));
                }
            }
        }
        log_line(&app_health, &format!("Backend health check FAILED — not listening on port {BACKEND_PORT} after 90 attempts"));
        let _ = app_health.emit("backend-status", "error: backend not reachable");
    });

    Ok(format!("Backend starting on port {BACKEND_PORT}"))
}
