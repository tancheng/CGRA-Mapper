/*************************************************************************
* Vectorized matrixmul Kernel
*************************************************************************/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <assert.h>
#include <stdbool.h>

#define DATA_TYPE
typedef double data_t;

#ifdef USE_RISCV_VECTOR
#include <riscv_vector.h>
#include "../../common/vector_defines.h"

void matrixmul_intrinsics(data_t *a, data_t *b, data_t *c, int n, int m, int p) {

    for (size_t i = 0; i < m; i++) {
        for (size_t j = 0; j < n; j++) {
            size_t gvl = _MMR_VSETVL_E64M1(p);
            vfloat64m1_t vprod = _MM_SET_f64(0, gvl);
            vfloat64m1_t vsum  = _MM_SET_f64(0, gvl);

            for (size_t k = 0; k < p; k += gvl){
                gvl = _MMR_VSETVL_E64M1(p - k);

                // Matrix A row
                vfloat64m1_t va  = _MM_LOAD_f64(&a[i*p+k], gvl);
                // Matrix B column
                vfloat64m1_t vb = _MM_LOAD_STRIDE_f64(&b[k*n+j], n * sizeof(data_t), gvl);

                // A[0]*B[0], A[1]*B[1],... A[n]*B[n]
                vprod  = _MM_MACC_f64(vprod,va, vb, gvl);

            }//k
            gvl = _MMR_VSETVL_E64M1(p);
            vsum   = _MM_REDSUM_f64(vprod,vsum, gvl);
            c[i*n+j] = _MM_VGETFIRST_f64(vsum);
        }//j
    }//i
}


#else // !USE_RISCV_VECTOR

void matmul_serial(data_t *a, data_t *b, data_t *c, int n, int m, int p) {
    int i = 0, j = 0, k = 0;
    c[i * n + j] += a[i * p + k] * b[k * n + j];
    // for (int i = 0; i < m; ++i)
    //     for (int j = 0; j < n; ++j) {
    //         c[i * n + j] = 0;
    //         for (int k = 0; k < p; ++k) {

        //     }
        // }
}

#endif


bool compare( size_t dm, size_t dn, data_t *a ,data_t *b) {
    bool result = false;
    for (int i = 0; i < dm; i++) {
        for (int j = 0; j < dn; j++) {
            if(a[i*dn+j] != b[i*dn+j]) {
              result = true;
            }
        }

    }
    return result;
}

void kernel_jacobi_2d(int tsteps,int n, int **A,int **B)
{
  int t, i, j;
#ifndef USE_RISCV_VECTOR
  for (t = 0; t < tsteps; t++)
    {
      for (i = 1; i < n - 1; i++)
       for (j = 1; j < n - 1; j++)
         B[i][j] = (0.2) * (A[i][j] + A[i][j-1] + A[i][1+j] + A[1+i][j] + A[i-1][j]);
    //   for (i = 1; i < n - 1; i++)
    //    for (j = 1; j < n - 1; j++)
    //      A[i][j] = (0.2) * (B[i][j] + B[i][j-1] + B[i][1+j] + B[1+i][j] + B[i-1][j]);
    }
#elif USE_LOOP_TILING
    for (t = 0; t < tsteps; t++)
    {
      kernel_jacobi_2d_vector_tiling(tsteps,n, A,B);
      kernel_jacobi_2d_vector_tiling(tsteps,n, B,A);
    }
#else
    for (t = 0; t < tsteps; t++)
    {
      kernel_jacobi_2d_vector(tsteps,n, A,B);
      kernel_jacobi_2d_vector(tsteps,n, B,A);
    }
#endif
}
