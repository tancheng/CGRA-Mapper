<pre>
========================================================

  _____________  ___     __  ___                      
 / ___/ ___/ _ \/ _ |   /  |/  /__ ____  ___  ___ ____
/ /__/ (_ / , _/ __ |  / /|_/ / _ `/ _ \/ _ \/ -_) __/
\___/\___/_/|_/_/ |_| /_/  /_/\_,_/ .__/ .__/\__/_/   
                                 /_/  /_/             

========================================================
</pre>


This is a CGRA (Coarse-Grained Reconfigurable Architecture) mapper to map the target loops onto the CGRA. The CGRA is parameterizable (e.g., CGRA size, type of the computing units in each tile, communication connection, etc.). Different advanced mapping strategies are built on top of this basic mapper. CGRA Mapper currently provides following features and functionalities:
- It takes the arch&kernel info in `JSON` format. 
- It can generate the DFG/CDFG of the target code region (in `.png`).
- Nested-loop and complex if/else control flows are supported with [partial predication](https://dl.acm.org/doi/abs/10.1145/2593069.2593100).
- A user can easily invoke loop-unrolling and loop-flattening in the compile script.
- It schedules and maps the DFG onto the CGRA arch that is represented in [MRRG](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=1188678).
- The generated dfg.json and config.json can be taken as inputs for the simulation in the [OpenCGRA](https://github.com/tancheng/OpenCGRA) (manual tunning might be needed for now).
- Benchmark including a set of representative kernels/applications with compilation scripts can be found [here](https://github.com/tancheng/CGRA-Bench).


Showcase
--------------------------------------------------------

```
// target FIR kernel
for (i = 0; i < NTAPS; ++i) {
    sum += input[i] * coefficient[i];
}
```
<p float="center">
  <img src="https://user-images.githubusercontent.com/6756658/131276748-779f92c6-6d9c-40ec-8868-ba95d44c5005.png" width="400" />
  <img src="https://user-images.githubusercontent.com/6756658/131276443-d5a7ffa4-cfd5-4e46-8fe1-98254abb9d03.png" width="250" /> 
</p>


Citation
--------------------------------------------------------------------------
```
@inproceedings{tan2020opencgra,
  title={OpenCGRA: An Open-Source Unified Framework for Modeling, Testing, and Evaluating CGRAs},
  author={Tan, Cheng and Xie, Chenhao and Li, Ang and Barker, Kevin J and Tumeo, Antonino},
  booktitle={2020 IEEE 38th International Conference on Computer Design (ICCD)},
  pages={381--388},
  year={2020},
  organization={IEEE}
}
```


License
--------------------------------------------------------------------------

CGRA-Mapper is offered under the terms of the Open Source Initiative BSD 3-Clause License. More information about this license can be found here:

  - http://choosealicense.com/licenses/bsd-3-clause
  - http://opensource.org/licenses/BSD-3-Clause


Build
--------------------------------------------------------

The mapper requires the following additional prerequisites:

 - LLVM 11.0
 - CMAKE 3.1


Execution
--------------------------------------------------------
```
 % opt -load ~/this repo/build/mapper/libmapperPass.so -mapperPass ~/target benchmark/target_kernel.bc
```


Related publications
--------------------------------------------------------------------------

- Cheng Tan, et al. _“DynPaC: Coarse-Grained, Dynamic, and Partially Reconfigurable Array for Streaming Applications.”_ The 39th IEEE International Conference on Computer Design. (ICCD'21), Oct 2021.
- Cheng Tan, et al. _“OpenCGRA: Democratizing Coarse-Grained Reconfigurable Arrays.”_ The 32nd IEEE International Conference on Application-specific Systems, Architectures and Processors (ASAP'21), A Virtual Conference, July 7-8, 2021.
- Cheng Tan, et al. _"ARENA: Asynchronous Reconfigurable Accelerator Ring to Enable Data-Centric Parallel Computing."_ IEEE Transactions on Parallel and Distributed Systems (TPDS'21).
- Cheng Tan, et al. _“AURORA: Automated Refinement of Coarse-Grained Reconfigurable Accelerators.”_ The 2021 Design, Automation & Test in Europe Conference, Grenoble, France. (DATE'21) February 1-5, 2021.
- Christopher Torng, et al. _"Ultra-Elastic CGRAs for Irregular Loop Specialization."_ 2021 IEEE International Symposium on High-Performance Computer Architecture (HPCA'21).
