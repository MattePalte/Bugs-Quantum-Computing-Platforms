Related to the C++ to Python mapping. The user writes code in python, then we have to map that call back to some code in C++, since Python doesn't have any type we have to match each vairable from Python to some type known to the C++ language. To do this mapping we have an ORDERED list of types which we try to map to. Bug map to vector<double> has higher priority than vector<complex>, so we might lose information by casting to double, because some times we need to reason on complex numbers. Thus the bug fix swap that order and converts to complex first, to let the C++ backend interpret the variable correctly.