<pre>
==========================================

 ___ ___   ____  ____  ____   ___  ____  
|   |   | /    ||    \|    \ /  _]|    \ 
| _   _ ||  o  ||  o  )  o  )  [_ |  D  )
|  \_/  ||     ||   _/|   _/    _]|    / 
|   |   ||  _  ||  |  |  | |   [_ |    \ 
|   |   ||  |  ||  |  |  | |     ||  .  \
|___|___||__|__||__|  |__| |_____||__|\_|
                                         

==========================================
</pre>


This is a CGRA (Coarse-Grained Reconfigurable Architecture) mapper to map the inner-most loop onto the CGRA. The CGRA is parameterizable (e.g., CGRA size, type of the computing units in each tile, communication connection, etc.). Different advanced mapping strategies are built on top of this basic mapper.


Related publications
--------------------------------------------------------------------------

- Cheng Tan, et al. _“AURORA: Automated Refinement of Coarse-Grained Reconfigurable Accelerators.”_ The 2021 Design, Automation & Test in Europe Conference, Grenoble, France. (DATE-21) February 1-5, 2021.
- Cheng Tan, et al. _"ARENA: Asynchronous Reconfigurable Accelerator Ring to Enable Data-Centric Parallel Computing."_ IEEE Transactions on Parallel and Distributed Systems (TPDS-21).
- Cheng Tan, et al. _"OpenCGRA: An Open-Source Framework for Modeling, Testing, and Evaluating CGRAs."_ The 38th IEEE International Conference on Computer Design. (ICCD-20), Oct 2020.  [Repo](https://github.com/pnnl/OpenCGRA).



License
--------------------------------------------------------------------------

OpenCGRA is offered under the terms of the Open Source Initiative BSD 3-Clause License. More information about this license can be found here:

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
