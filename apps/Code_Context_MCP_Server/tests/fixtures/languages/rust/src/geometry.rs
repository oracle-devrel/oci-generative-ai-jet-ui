/// A circle.
#[derive(Debug, Clone)]
pub struct Circle {
    r: f64,
}

pub trait Shape {
    fn area(&self) -> f64;
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        square(self.r) * std::f64::consts::PI
    }
}

impl Circle {
    pub fn new(r: f64) -> Self {
        Circle { r }
    }

    pub fn scale(self) -> Self {
        println!("scaled {}", self.area());
        self
    }
}

pub enum Kind {
    Round,
}

fn square(x: f64) -> f64 {
    x * x
}
