# PORT.md — building CGRA-Mapper against LLVM 19

This branch (`llvm19`) makes upstream CGRA-Mapper build and run against
**LLVM 19** instead of the LLVM 12 it was written for in 2020.

## Why this branch exists

The host distribution is Debian 13, which ships clang/LLVM 17, 18, 19, 21
and 22 — **LLVM 12 is not available and cannot be installed from apt**. The
consumer of this branch is the `CGRAs-PingPong` simulator, which vendors a
`cgra/test/config_fir.json` that was produced by this mapper (it is byte
identical to a mapper output, and its `dfg.json` sibling matches this
project's early-2020 schema). Rebuilding that artifact requires the mapper
to run, and the mapper must be built and loaded by the **same** LLVM
version: upstream's own README says *"The pass should be built and run with
the same version of the LLVM."*

Target chosen: **LLVM 19.1.7**, because it is already installed —
`/usr/bin/{clang-19, opt-19, llvm-config-19}` and the CMake package at
`/usr/lib/llvm-19/lib/cmake/llvm`.

## The whole port is two files

```
 CMakeLists.txt     |  4 ++-
 src/mapperPass.cpp | 79 ++++++++++++++++++++++++++++++++++++++-----------------
 2 files changed, 57 insertions(+), 26 deletions(-)
```

Notably **nothing else needed changing**. `Mapper.cpp` (75 KB), `DFG.cpp`
(62 KB), `DFGNode.cpp`, `CGRA.cpp`, `CGRANode.cpp`, `CGRALink.cpp` and the
headers all compiled unmodified. This was verified by inspection before the
first build attempt and then confirmed by it: the codebase keeps LLVM at
arm's length — `Mapper.cpp` includes **no LLVM headers at all**, `DFG.cpp`
includes only `<fstream>` and its own header and never inspects a `Type`,
and no file anywhere uses a typed-pointer API (`getPointerElementType`,
`PointerType`, `DataLayout`, `CreateGEP` are absent from the whole tree), so
LLVM 15's opaque-pointer migration — normally the expensive part of a port
like this — is a non-issue here.

## Change 1 — `CMakeLists.txt`: C++17

```cmake
-set(CMAKE_CXX_STANDARD 14)
+set(CMAKE_CXX_STANDARD 17)
```

LLVM 19's headers require C++17 (`std::is_class_v`, `std::is_pointer_v`,
`std::optional`, `std::size`). With C++14 the build produced **3418
errors**, every one of them from inside `/usr/lib/llvm-19/include/` rather
than from this project's own code. Raising the standard took that to zero.

`llvm-config-19 --cxxflags` agrees: it emits `-std=c++17`.

## Change 2 — `mapperPass.cpp`: register as a new pass manager plugin

**The legacy pass manager API still compiles against LLVM 19.** Debian's
package still ships `llvm/Pass.h`, so `struct mapperPass : public
FunctionPass`, `RegisterPass<>`, `getAnalysisUsage` and
`getAnalysis<LoopInfoWrapperPass>()` all build without complaint.

What is gone is the **invocation**. Running the upstream form

```
opt-19 -load build/src/libmapperPass.so -mapperPass kernel.bc
```

fails with:

```
The `opt -passname` syntax for the new pass manager is not supported,
please use `opt -passes=<pipeline>` (or the `-p` alias for a more concise version).
```

So the pass has to be *registered* as a plugin and *invoked* through a
pipeline, even though the old headers would still let it build. The
conversion is mechanical:

| legacy | new |
|---|---|
| `struct mapperPass : public FunctionPass` | `struct mapperPass : public PassInfoMixin<mapperPass>` |
| `bool runOnFunction(Function&) override` | `PreservedAnalyses run(Function&, FunctionAnalysisManager&)` |
| `return false;` / `return true;` at the end of the function body | `return PreservedAnalyses::all()` (see the note below) |
| `static char ID;` + `RegisterPass<mapperPass> X(...)` | `llvmGetPassPluginInfo` + `registerPipelineParsingCallback` |
| `getAnalysis<LoopInfoWrapperPass>().getLoopInfo()` | `FAM.getResult<LoopAnalysis>(F)` |

Two details worth knowing if this is ever rebased:

**`getAnalysis` was called from a helper, not from the entry point.**
`getTargetLoops()` (not `runOnFunction`) is where the `LoopInfo` was
fetched, so the analysis result has to be threaded in as a parameter rather
than looked up in place. The signature gained a `LoopInfo&`.

**Only the function-body returns change.** `run()`'s early exits and its
normal end become `PreservedAnalyses::all()` — the pass only reads the IR
(it builds its own DFG/CGRA model and writes JSON), which is exactly what
the legacy `return false` + `setPreservesAll()` meant. `canMap()`, a helper
that genuinely returns `bool`, keeps `return true;` / `return false;`.
Getting this backwards compiles fine right up until the return type is
checked, and the two functions end adjacently, so it is easy to conflate.

## Change 3 — `mapperPass.cpp`: `json` is ambiguous

Including `llvm/Passes/PassBuilder.h` (needed for change 2) transitively
pulls in `llvm/Support/JSON.h`, which declares `llvm::json`. Under the
file's `using namespace llvm` that makes a bare `json` ambiguous with the
file's own `using json = nlohmann::json;`.

The alias is dropped and the **four** uses are spelled `nlohmann::json`
(`json::out_of_range` becomes `nlohmann::json::out_of_range`). A
file-scope rename would also work but touches more lines than it needs to.

## Two upstream footguns, both silent

Neither is a porting defect, but both cost real debugging time and would
cost it again to anyone picking this up.

**1. `-O0` makes the pass a no-op.** The upstream `test/compile.sh` compiles
the kernel with `clang -O0`, and clang at `-O0` marks every function
`optnone noinline`, which the new pass manager honours by **skipping
non-required passes entirely**. The result is `opt` exiting 0, printing
nothing, and writing no JSON. `-debug-pass-manager` is what shows it:

```
Skipping pass {anonymous}::mapperPass on _Z6kernelPfS_S_ due to optnone attribute
```

The `-O0` in that script is a legacy-pass-manager-era choice; compile at
`-O3` (or pass `-Xclang -disable-O0-optnone`) instead.

**2. `-O3` alone fuses the MAC into an FMA and mapping fails.** For
`output[j] += input[i] * coefficient[i]`, `-O3` emits `llvm.fmuladd.f32`,
which no functional unit in this mapper's list implements, so the run ends
in `[canMap] Missing functional units: llvm.fmuladd.f32` /
`[Mapping Fail]`. Add `-ffp-contract=off`.

## Verified invocation

```bash
cmake -S . -B build -DLLVM_DIR=/usr/lib/llvm-19/lib/cmake/llvm
cmake --build build -j4                       # -> build/src/libmapperPass.so

clang-19 -emit-llvm -fno-unroll-loops -ffp-contract=off -O3 \
         -o kernel.bc -c test/kernel.cpp
opt-19 -load-pass-plugin=build/src/libmapperPass.so \
       -passes='function(mapperPass)' -disable-output kernel.bc
```

Note `-passes='function(mapperPass)'`, not a bare `-passes=mapperPass`: the
pass registers itself through the *function*-pipeline callback, and a bare
name at the top level is looked up in the *module* pipeline registry, where
it is not found. (A bare `-passes=mapperPass` does not error — it simply
parses to a pipeline that never contains the pass, which is another silent
failure mode.)

Outputs, written to the working directory: `dfg.json`, `config.json`,
`increMapInput.json`, and `_Z6kernelPfS_S_.dot`.

## What the ported build reproduces

Against `test/kernel.cpp` (the FIR kernel) with `test/param.json`
(`row:4, column:4`, `isTrimmedDemo:true`) on a 4×4 array, the LLVM 19 build
produces:

* a DFG of **11 nodes / 15 edges**, matching the vendored golden `dfg.json`
  exactly in node and edge count;
* opcode populations `phi 2, getelementptr 2, load 2, mul 1, add 1, cmp 1,
  br 1` — all present in the golden DFG;
* `[ResMII: 1]`, `[RecMII: 2]`, and — after the algorithm's `II = II + 1`
  retry loop runs — a final **II of 4**, the same II as the golden config;
* a `config.json` with the golden's exact key set
  (`x, y, cycle, opt, predicate, out_0..out_7`) that the downstream
  simulator's `CGRACtrl` parses without complaint.

The residual difference is one `store` node in the new DFG that the golden
does not have (and its address computation, which accounts for the extra
`ADD`/`ADD_CONST`/`LD`/`STR` in the emitted control words). That traces to
the **compile flags** of whatever build produced the golden artifact in
2020, not to the port: the original clang invocation is not recorded
anywhere in this repository or in the simulator's.

## Not done

`-DLLVM_DIR` is passed by hand; there is no CMake-side LLVM version check, so
building against a different LLVM than the `opt` that loads the plugin is
still possible and will fail at load time rather than at configure time.
Worth adding when this is wired into a build system.
