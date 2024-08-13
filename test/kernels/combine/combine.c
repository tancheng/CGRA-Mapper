/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#define SIZE1 1000

float** A;
float** B;
float** output;

void kernel(int, int, int, float** A, float** B, float** output);

int main()
{

  kernel(5, 6, 7, A, B, output);

  return 0;
}

void kernel(int I, int J, int K, float** A, float** B, float** output)
{
  int i = 0;
  int j = 0;
  int k = 0;

  /*
  for (i = 0; i < I; ++i) {
    for (j = 0; j < J; ++j) {
      for (k = 0; k < K; ++k) {
        output[i][j] += A[i][k] * B[k][j];
      }
    }
  }
  */

  int X = I*J*K;
  int x = 0;
  for (x = 0; x < X; ++x) {
    i = x / (J * K);
    k = (x / J) % K;
    j = x % J;
    output[i][j] += A[i][k] * B[k][j];
  }

}

