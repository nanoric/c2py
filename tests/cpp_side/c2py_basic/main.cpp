#include <gtest/gtest.h>

#ifdef ARDUINO
void setup() {
    // Since Arduino doesn't have a command line, fake out the argc/argv arguments
    int argc = 1;
    const auto arg0 = "PlatformIO";
    char* argv0 = const_cast<char*>(arg0);
    char** argv = &argv0;

    testing::InitGoogleTest(&argc, argv);
}

void loop() { RUN_ALL_TESTS(); }

#else

GTEST_API_ int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
#endif