use std::{
    io::{BufRead, BufReader, Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};

use serde::Serialize;
use tauri::{AppHandle, Emitter};

const BACKEND_ADDRESS: &str = "127.0.0.1:8095";
const HEALTH_ATTEMPTS: usize = 50;
const HEALTH_RETRY_DELAY: Duration = Duration::from_millis(200);
const HEALTH_IO_TIMEOUT: Duration = Duration::from_millis(250);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BackendSnapshot {
    pub status: String,
    pub logs: Vec<String>,
}

impl Default for BackendSnapshot {
    fn default() -> Self {
        Self {
            status: "initializing".to_string(),
            logs: Vec::new(),
        }
    }
}

#[derive(Clone, Default)]
pub struct BackendProcess {
    child: Arc<Mutex<Option<Child>>>,
    snapshot: Arc<Mutex<BackendSnapshot>>,
}

impl BackendProcess {
    pub fn start(&self, app: AppHandle) -> Result<(), String> {
        let script = backend_script_path();

        emit_status(&app, self, "starting");
        emit_log(
            &app,
            self,
            format!("Starting backend: {}", script.display()),
        );

        let mut child = Command::new(&script)
            .env("AVALON_TAURI_MANAGED", "1")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| {
                format!("Failed to start backend via {}: {error}", script.display())
            })?;

        if let Some(stdout) = child.stdout.take() {
            forward_output(app.clone(), self.clone(), "stdout", stdout);
        }

        if let Some(stderr) = child.stderr.take() {
            forward_output(app.clone(), self.clone(), "stderr", stderr);
        }

        {
            let mut stored_child = self
                .child
                .lock()
                .map_err(|_| "Backend process lock is poisoned".to_string())?;
            *stored_child = Some(child);
        }

        let process = self.clone();
        thread::spawn(move || wait_for_readiness(app, process));

        Ok(())
    }

    pub fn stop(&self) {
        let Ok(mut stored_child) = self.child.lock() else {
            eprintln!("[backend] failed to acquire backend process lock during shutdown");
            return;
        };

        let Some(mut child) = stored_child.take() else {
            return;
        };

        if let Err(error) = child.kill() {
            eprintln!("[backend] failed to kill backend process: {error}");
        }

        if let Err(error) = child.wait() {
            eprintln!("[backend] failed to wait for backend process: {error}");
        }
    }

    pub fn snapshot(&self) -> Result<BackendSnapshot, String> {
        self.snapshot
            .lock()
            .map(|snapshot| snapshot.clone())
            .map_err(|_| "Backend snapshot lock is poisoned".to_string())
    }

    fn set_status(&self, status: &str) {
        match self.snapshot.lock() {
            Ok(mut snapshot) => {
                snapshot.status = status.to_string();
            }
            Err(error) => {
                eprintln!("[backend] failed to update backend status snapshot: {error}");
            }
        }
    }

    fn add_log(&self, message: &str) {
        match self.snapshot.lock() {
            Ok(mut snapshot) => {
                snapshot.logs.push(message.to_string());
            }
            Err(error) => {
                eprintln!("[backend] failed to update backend log snapshot: {error}");
            }
        }
    }

    fn exit_status(&self) -> Option<String> {
        let Ok(mut stored_child) = self.child.lock() else {
            return Some("backend process lock is poisoned".to_string());
        };

        let child = stored_child.as_mut()?;

        match child.try_wait() {
            Ok(Some(status)) => Some(status.to_string()),
            Ok(None) => None,
            Err(error) => Some(format!("could not inspect backend process: {error}")),
        }
    }
}

fn backend_script_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("scripts")
        .join("others")
        .join("start-backend.sh")
}

fn forward_output<R>(app: AppHandle, process: BackendProcess, stream: &'static str, reader: R)
where
    R: Read + Send + 'static,
{
    thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            match line {
                Ok(line) => {
                    println!("[backend:{stream}] {line}");
                    emit_log(&app, &process, format!("[{stream}] {line}"));
                }
                Err(error) => {
                    eprintln!("[backend:{stream}] failed to read backend output: {error}");
                    emit_log(
                        &app,
                        &process,
                        format!("[{stream}] Failed to read backend output: {error}"),
                    );
                    break;
                }
            }
        }
    });
}

fn wait_for_readiness(app: AppHandle, process: BackendProcess) {
    emit_status(&app, &process, "waiting-for-health");
    emit_log(
        &app,
        &process,
        "Waiting for backend health endpoint".to_string(),
    );

    for _ in 0..HEALTH_ATTEMPTS {
        if backend_is_healthy(BACKEND_ADDRESS) {
            emit_log(&app, &process, "Backend ready".to_string());
            emit_status(&app, &process, "ready");
            return;
        }

        if let Some(status) = process.exit_status() {
            emit_log(
                &app,
                &process,
                format!("Backend exited before becoming ready: {status}"),
            );
            emit_status(&app, &process, "failed");
            return;
        }

        thread::sleep(HEALTH_RETRY_DELAY);
    }

    emit_log(
        &app,
        &process,
        "Backend health check timed out after 10 seconds".to_string(),
    );
    emit_status(&app, &process, "failed");
}

fn backend_is_healthy(address: &str) -> bool {
    let Ok(socket_address) = address.parse::<SocketAddr>() else {
        return false;
    };

    let Ok(mut stream) = TcpStream::connect_timeout(&socket_address, HEALTH_IO_TIMEOUT) else {
        return false;
    };

    let _ = stream.set_read_timeout(Some(HEALTH_IO_TIMEOUT));
    let _ = stream.set_write_timeout(Some(HEALTH_IO_TIMEOUT));

    if stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200")
}

fn emit_status(app: &AppHandle, process: &BackendProcess, status: &str) {
    process.set_status(status);
    println!("[backend] status={status}");
    if let Err(error) = app.emit("backend-status", status) {
        eprintln!("[backend] failed to emit backend-status event: {error}");
    }
}

fn emit_log(app: &AppHandle, process: &BackendProcess, message: String) {
    process.add_log(&message);
    println!("[backend] {message}");
    if let Err(error) = app.emit("backend-log", message) {
        eprintln!("[backend] failed to emit backend-log event: {error}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::TcpListener;

    #[test]
    fn backend_script_resolves_from_project_root() {
        let script = backend_script_path();

        assert!(script.ends_with("scripts/others/start-backend.sh"));
        assert!(script.is_file());
    }

    #[test]
    fn health_check_accepts_http_200() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();

        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut request = [0_u8; 512];
            let _ = stream.read(&mut request);
            stream
                .write_all(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}",
                )
                .unwrap();
        });

        assert!(backend_is_healthy(&address.to_string()));
        server.join().unwrap();
    }

    #[test]
    fn health_check_rejects_non_200_response() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();

        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut request = [0_u8; 512];
            let _ = stream.read(&mut request);
            stream
                .write_all(
                    b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
                )
                .unwrap();
        });

        assert!(!backend_is_healthy(&address.to_string()));
        server.join().unwrap();
    }
}
