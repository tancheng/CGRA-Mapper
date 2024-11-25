/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#define SIZE1 1000

float** A;
float* output;

void kernel(int, int, float**, float*);

int main()
{

  kernel(5, 6, A, output);

  return 0;
}

void kernel(int I, int J, float** A, float* output)
{
  int i = 0;
  int j = 0;

  /*
  for (i = 0; i < I; ++i) {
    for (j = 0; j < J; ++j) {
      output[j] += A[i][j];
    }
  }
  */

  int X = I*J;
  int x = 0;
  for (x = 0; x < X; ++x) {
    i = x / J;
    j = x % J;
    output[j] += A[i][j];
  }

}

