//! Geometry for the demo.

mod geometry;

use crate::geometry::Circle;
use std::fmt;

/// Makes a circle.
pub fn make() -> Circle {
    Circle::new(1.0).scale()
}

fn helper() -> fmt::Result {
    Ok(())
}
