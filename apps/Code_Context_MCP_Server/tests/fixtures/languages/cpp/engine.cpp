#include "engine.h"

namespace app {

/// Starts the engine.
void app::Engine::start() {
    warm();
    this->speed();
    Helper::run();
}

template <typename T>
T maxof(T a, T b) {
    return a > b ? a : b;
}

int main() {
    Engine e;
    e.start();
    return maxof(1, 2);
}

}  // namespace app
