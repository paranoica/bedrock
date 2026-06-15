#include <vector>

int sum_with_first(std::vector<int>& v, int n) {
    v.reserve(v.size() + n);    // no reallocation during the loop...
    int first = v[0];           // ...but still copy the value, don't hold a reference
    for (int i = 0; i < n; ++i)
        v.push_back(i);
    return first + v.back();
}
