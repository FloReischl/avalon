use raw_window_handle::{HasWindowHandle, RawWindowHandle};
use serde::Deserialize;
use x11rb::{
    connection::Connection,
    protocol::{
        shape::{ConnectionExt as _, SK, SO},
        xproto::{ClipOrdering, Rectangle},
    },
};

const MAX_INPUT_RECTANGLES: usize = 20_000;

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InputRect {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

pub fn set_window_input_regions(
    window: &tauri::WebviewWindow,
    rectangles: Vec<InputRect>,
) -> Result<(), String> {
    if rectangles.len() > MAX_INPUT_RECTANGLES {
        return Err(format!(
            "Input shape contains too many rectangles: {} > {}",
            rectangles.len(),
            MAX_INPUT_RECTANGLES
        ));
    }

    let window_handle = window
        .window_handle()
        .map_err(|error| format!("Failed to get native window handle: {error}"))?;

    let window_id = match window_handle.as_raw() {
        RawWindowHandle::Xlib(handle) => u32::try_from(handle.window)
            .map_err(|_| "Xlib window id does not fit into u32".to_string())?,
        RawWindowHandle::Xcb(handle) => handle.window.get(),
        _ => return Err("Pixel input shaping is currently supported only on X11".to_string()),
    };

    let x11_rectangles = rectangles
        .into_iter()
        .map(to_x11_rectangle)
        .collect::<Result<Vec<_>, _>>()?;

    let (connection, _) = x11rb::connect(None)
        .map_err(|error| format!("Failed to connect to X11 server: {error}"))?;

    connection
        .shape_query_version()
        .map_err(|error| format!("Failed to query X11 SHAPE extension: {error}"))?
        .reply()
        .map_err(|error| format!("X11 SHAPE extension is unavailable: {error}"))?;

    connection
        .shape_rectangles(
            SO::SET,
            SK::INPUT,
            ClipOrdering::UNSORTED,
            window_id,
            0,
            0,
            &x11_rectangles,
        )
        .map_err(|error| format!("Failed to set X11 input shape: {error}"))?
        .check()
        .map_err(|error| format!("X11 rejected input shape: {error}"))?;

    connection
        .flush()
        .map_err(|error| format!("Failed to flush X11 input shape: {error}"))?;

    println!(
        "[input-shape] applied {} X11 input rectangles",
        x11_rectangles.len()
    );

    Ok(())
}

fn to_x11_rectangle(rectangle: InputRect) -> Result<Rectangle, String> {
    if rectangle.width == 0 || rectangle.height == 0 {
        return Err("Input shape rectangles must have non-zero size".to_string());
    }

    Ok(Rectangle {
        x: i16::try_from(rectangle.x)
            .map_err(|_| format!("Input rectangle x is out of range: {}", rectangle.x))?,
        y: i16::try_from(rectangle.y)
            .map_err(|_| format!("Input rectangle y is out of range: {}", rectangle.y))?,
        width: u16::try_from(rectangle.width)
            .map_err(|_| format!("Input rectangle width is out of range: {}", rectangle.width))?,
        height: u16::try_from(rectangle.height).map_err(|_| {
            format!(
                "Input rectangle height is out of range: {}",
                rectangle.height
            )
        })?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn converts_valid_input_rectangle() {
        let rectangle = to_x11_rectangle(InputRect {
            x: 12,
            y: 34,
            width: 56,
            height: 78,
        })
        .unwrap();

        assert_eq!(rectangle.x, 12);
        assert_eq!(rectangle.y, 34);
        assert_eq!(rectangle.width, 56);
        assert_eq!(rectangle.height, 78);
    }

    #[test]
    fn rejects_empty_input_rectangle() {
        let result = to_x11_rectangle(InputRect {
            x: 0,
            y: 0,
            width: 0,
            height: 10,
        });

        assert!(result.is_err());
    }

    #[test]
    fn rejects_coordinates_outside_x11_range() {
        let result = to_x11_rectangle(InputRect {
            x: i32::MAX,
            y: 0,
            width: 10,
            height: 10,
        });

        assert!(result.is_err());
    }
}
