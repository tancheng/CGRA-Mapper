#define NTAPS 2048

int input[NTAPS], output[NTAPS];

void kernel(int* __restrict__ input, int* __restrict__ output);

int main()
{
    kernel(input, output);

    return 0;
}

void kernel(int* __restrict__ input, int* __restrict__ output)
/*   input :           input sample array */
/*   output:           output sample array */
{   
    #pragma clang loop vectorize(enable)
    for (int i = 0; i < NTAPS; i++) {
        int x = input[i];
        output[i] = x / 3;
    }
}