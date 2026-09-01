mod backend;
mod input_shape;

use backend::{BackendProcess, BackendSnapshot};
use input_shape::InputRect;
use tauri::Manager;

#[tauri::command]
fn get_backend_snapshot(
    backend: tauri::State<'_, BackendProcess>,
) -> Result<BackendSnapshot, String> {
    backend.snapshot()
}

#[tauri::command]
fn set_window_input_regions(
    window: tauri::WebviewWindow,
    rectangles: Vec<InputRect>,
) -> Result<(), String> {
    input_shape::set_window_input_regions(&window, rectangles)
}

fn main() {
    let backend = BackendProcess::default();

    let app = tauri::Builder::default()
        .manage(backend.clone())
        .invoke_handler(tauri::generate_handler![
            get_backend_snapshot,
            set_window_input_regions
        ])
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
