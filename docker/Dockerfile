FROM ubuntu:22.04

RUN apt-get -y update \
    && apt-get -y install llvm-12 llvm-12-dev llvm-12-tools clang-12 \
    && apt-get -y install cmake \
    && mkdir ${HOME}/cgra \
    && cd ${HOME}/cgra \
    && apt-get -y install git \
    && git clone https://github.com/tancheng/CGRA-Mapper.git \
    && apt-get -y install build-essential \
    && cd CGRA-Mapper && mkdir build && cd build && cmake .. \
    && make

CMD ["tail", "-f", "/dev/null"]
