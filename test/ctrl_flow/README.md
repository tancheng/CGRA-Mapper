# Parameters in `param.json` related to control flow fusion
1. `fusionStrategy` has three optional values: `default_heterogeneous`, `nonlinear`, and `ctrl_flow`.

2. User can specify the patteren to be fused using `fusionPattern` when `ctrl_flow` is a value of `fusionStrategy`. The user-specified pattern takes precedence during fusion.