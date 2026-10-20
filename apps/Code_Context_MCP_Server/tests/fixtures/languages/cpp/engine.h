#include <vector>

namespace app {

/// An engine.
class Engine {
public:
    void start();
    int speed() const { return 1; }

private:
    void warm() {}
};

struct Point {
    int x;
};

enum class Mode { On, Off };

}  // namespace app
