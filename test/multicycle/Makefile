MAPPER_SRC ?= /WORK_REPO/CGRA-Mapper
MAPPER_BUILD_DIR ?= $(MAPPER_SRC)/build
PASS_DIR ?= $(MAPPER_BUILD_DIR)/src
BUILD_DIR ?= $(CURDIR)/build

KERNEL := kernel
.PHONY: relu conv spmv histogram latnrm dtw fft mvt fir gemm resnet ln1 ln2 mask softmax1 softmax2 harris1 harris2 harris3 harris4 gelu

run: 
	clang-12 -emit-llvm -O3 -fno-unroll-loops -fno-vectorize -o multicycle_test.bc -c multicycle_test.cpp 
	opt-12 -load /WORK_REPO/CGRA-Mapper/build/src/libmapperPass.so -mapperPass multicycle_test.bc
	llvm-dis-12 multicycle_test.bc -o multicycle_test.ll
	dot -Tpng _Z6kernelPiS_.dot -o multicycle_test.png

# "load", "store", "udiv", "urem"

clean:
	rm -rf $(BUILD_DIR)/*.dot
	rm -rf $(BUILD_DIR)/*.ll
	rm -rf $(BUILD_DIR)/*.bc
	rm -rf $(BUILD_DIR)/*.json

move:
	mv $(BUILD_DIR)/*.png ../../dfg/fused/activation/