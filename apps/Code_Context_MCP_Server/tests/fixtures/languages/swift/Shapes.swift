import Foundation

/// A circle.
struct Circle {
    var r: Double
}

protocol Shape {
    func area() -> Double
}

extension Circle: Shape {
    func area() -> Double {
        let s = self.scale()
        return square(r) * s
    }

    private func scale() -> Double {
        return 1
    }
}

class Engine {
    init() {
        start()
    }

    func start() {
        Circle(r: 1).area()
    }
}

enum Kind {
    case round
}

func square(_ x: Double) -> Double {
    return x * x
}
