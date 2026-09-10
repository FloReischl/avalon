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

#[tauri::command]
fn resize_avatar_window(
    window: tauri::WebviewWindow,
    width: f64,
    height: f64,
) -> Result<(), String> {
    if !width.is_finite() || !height.is_finite() || width <= 0.0 || height <= 0.0 {
        return Err("Avatar window size must be finite and positive".to_string());
    }

    window
        .set_size(tauri::LogicalSize::new(width, height))
        .map_err(|error| error.to_string())?;

    Ok(())
}

#[tauri::command]
fn show_chat_window(app: tauri::AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("chat")
        .ok_or_else(|| "Chat window not found".to_string())?;

    window.unminimize().map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())?;

    Ok(())
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) {
    app.exit(0);
}

fn main() {
    let backend = BackendProcess::default();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .manage(backend.clone())
        .invoke_handler(tauri::generate_handler![
            get_backend_snapshot,
            set_window_input_regions,
            resize_avatar_window,
            show_chat_window,
            exit_app
        ])
        .setup(move |app| {
            let icon = tauri::include_image!("./icons/icon.png");

            for label in ["main", "chat"] {
                let window = app
                    .get_webview_window(label)
                    .ok_or_else(|| std::io::Error::other(format!("window '{label}' not found")))?;

                window
                    .set_icon(icon.clone())
                    .map_err(std::io::Error::other)?;
            }

            backend
                .start(app.handle().clone())
                .map_err(std::io::Error::other)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Avalo");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::WindowEvent {
            label,
            event: tauri::WindowEvent::CloseRequested { api, .. },
            ..
        } = &event
        {
            if label == "main" {
                app_handle.exit(0);
            } else if label == "chat" {
                api.prevent_close();

                if let Some(window) = app_handle.get_webview_window("chat") {
                    if let Err(error) = window.hide() {
                        eprintln!("failed to hide Avalo chat window: {error}");
                    }
                }
            }
        }

        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
        ) {
            app_handle.state::<BackendProcess>().stop();
        }
    });
}
