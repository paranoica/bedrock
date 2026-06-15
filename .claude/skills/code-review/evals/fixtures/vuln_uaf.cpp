#include <vector>

int sum_with_first(std::vector<int>& v, int n) {
    int& first = v[0];          // reference into the buffer
    for (int i = 0; i < n; ++i)
        v.push_back(i);         // reallocation invalidates `first` -> use-after-free read
    return first + v.back();    // `first` now dangles into freed storage
}
