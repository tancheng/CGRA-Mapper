#define NTAPS 2048

float input[NTAPS], output[NTAPS];

void kernel(float* input, float* output);

int main()
{
    kernel(input, output);

    return 0;
}

__attribute__((noinline)) float fp2fx(float x) {
    return x + 1.0;    
}

void kernel(float* input, float* output)
/*   input :           input sample array */
/*   output:           output sample array */
{   
    for (int i = 0; i < NTAPS; i++) {
        float x  = fp2fx(input[i]);
        output[i] = x * (float)2.0 + ((float)3.0 + x);
    }
}