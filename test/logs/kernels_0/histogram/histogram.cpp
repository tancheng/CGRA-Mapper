 
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <float.h>

#include <string.h>
#include <unistd.h>

#define DATA_LEN 20
#define BUCKET_LEN 5
#define MIN 1.0
#define MAX 19.0

void kernel(float input_data[], int histogram[]);
void output();

float input_data[DATA_LEN] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,14,14,14,14,14,19};
int histogram[BUCKET_LEN] = {0};

////////////////////////////////////////////////////////////////////////////////
// Program main
////////////////////////////////////////////////////////////////////////////////
int main( int argc, char** argv) {

  printf("DATA_LEN %d BUCKET_LEN %d\n",DATA_LEN, BUCKET_LEN);
  kernel(input_data, histogram);
  output();
	
  return 0;
}
 
void kernel(float input[], int histogram[]) {
  int i;
  float dmin = (float)MIN;
  float delt = (float)(MAX - dmin);

  //#pragma clang loop vectorize(enable) vectorize_width(4) unroll_count(4)
  for (i = 0; i < DATA_LEN; i++) {
    float r = BUCKET_LEN * (input[i] - dmin) / delt;
    int b = (int)(r);
    histogram[b]++;
  }
}

void output() {
  printf("len %d\n", BUCKET_LEN);
  printf("min %f\n", MIN);
  printf("del %f\n", MAX-MIN);
  for (int i = 0; i < BUCKET_LEN; i++)
    printf("%d ", histogram[i]);
  printf("\n");
}
