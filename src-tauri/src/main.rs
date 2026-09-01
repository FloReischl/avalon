mod backend;

use backend::{BackendProcess, BackendSnapshot};
use tauri::Manager;

#[tauri::command]
fn get_backend_snapshot(
    backend: tauri::State<'_, BackendProcess>,
) -> Result<BackendSnapshot, String> {
    backend.snapshot()
}

fn main() {
    let backend = BackendProcess::default();

    let app = tauri::Builder::default()
        .manage(backend.clone())
        .invoke_handler(tauri::generate_handler![get_backend_snapshot])
        .setup(move |app| {
            backend
                .start(app.handle().clone())
                .map_err(std::io::Error::other)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Avalo");

    app.run(|app_handle, event| {
        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
        ) {
            app_handle.state::<BackendProcess>().stop();
        }
    });
}
