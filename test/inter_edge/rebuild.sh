cd ../../build
cmake -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="-g" ..
ninja
cd ../test/inter_edge_test