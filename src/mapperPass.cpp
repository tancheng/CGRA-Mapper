/*
 * ======================================================================
 * mapperPass.cpp
 * ======================================================================
 * Mapper pass implementation.
 *
 * Author : Cheng Tan
 *   Date : Aug 16, 2021
 */

#include <llvm/IR/Function.h>
#include <llvm/Pass.h>
#include <llvm/Analysis/LoopInfo.h>
#include <llvm/Analysis/LoopIterator.h>
#include <stdio.h>
#include <fstream>
#include <iostream>
#include <set>
#include "json.hpp"
#include "Mapper.h"

// Used to walkaround the mis-interpret of LLVM opcode in github
// testing infra: https://github.com/tancheng/CGRA-Mapper/pull/27#issuecomment-2495202802
extern int testing_opcode_offset;

using namespace llvm;
using namespace std;
using json = nlohmann::json;
using namespace chrono;

void addDefaultKernels(map<string, list<int>*>*);

namespace {

  struct mapperPass : public FunctionPass {

  public:
    static char ID;
    Mapper* mapper;
    mapperPass() : FunctionPass(ID) {}

    void getAnalysisUsage(AnalysisUsage &AU) const override {
      AU.addRequired<LoopInfoWrapperPass>();
      AU.addPreserved<LoopInfoWrapperPass>();
      AU.setPreservesAll();
    }

    bool runOnFunction(Function &t_F) override {

      // Initializes input parameters.
      int rows                      = 4;
      int columns                   = 4;
      bool targetEntireFunction     = false;
      bool targetNested             = false;
      bool doCGRAMapping            = true;
      bool isStaticElasticCGRA      = false;
      bool isTrimmedDemo            = true;
      int ctrlMemConstraint         = 200;
      int bypassConstraint          = 4;
      int regConstraint             = 8;
      bool precisionAware           = false;
      bool diagonalVectorization    = false;
      bool heterogeneity            = false;
      int  PathSupportDim           = 16;
      bool heuristicMapping         = true;
      bool parameterizableCGRA      = false; 

      // Incremental mapping related:
      // https://github.com/tancheng/CGRA-Mapper/pull/24
      bool incrementalMapping       = false;

      // DVFS-related options.
      bool supportDVFS              = false;
      bool DVFSAwareMapping         = false;
      int DVFSIslandDim             = 2;
      bool enablePowerGating        = false;

      // Option used to split one integer division into 4.
      // https://github.com/tancheng/CGRA-Mapper/pull/27#issuecomment-2480362586
      int vectorFactorForIdiv               = 1;

      map<string, int>* execLatency = new map<string, int>();
      list<string>* pipelinedOpt    = new list<string>();
      map<string, list<int>*>* additionalFunc = new map<string, list<int>*>();
      map<string, list<string>*>* fusionPattern = new map<string, list<string>*>();

      // Set the target function and loop.
      map<string, list<int>*>* functionWithLoop = new map<string, list<int>*>();
      addDefaultKernels(functionWithLoop);

      // Read the parameter JSON file.
      ifstream i("./param.json");
      if (!i.good()) {

        cout<< "=============================================================\n";
        cout<<"\033[0;31mPlease provide a valid <param.json> in the current directory."<<endl;
        cout<<"A set of default parameters is leveraged.\033[0m"<<endl;
        cout<< "=============================================================\n";
      } else {
        json param;
        i >> param;
 
	// Check param exist or not.
	set<string> paramKeys;
	paramKeys.insert("row");
	paramKeys.insert("column");
	paramKeys.insert("targetFunction");
	paramKeys.insert("kernel");
	paramKeys.insert("targetNested");
	paramKeys.insert("targetLoopsID");
	paramKeys.insert("isTrimmedDemo");
	paramKeys.insert("doCGRAMapping");
	paramKeys.insert("isStaticElasticCGRA");
	paramKeys.insert("ctrlMemConstraint");
	paramKeys.insert("bypassConstraint");
	paramKeys.insert("regConstraint");
	paramKeys.insert("precisionAware");
	paramKeys.insert("diagonalVectorization");
	paramKeys.insert("heterogeneity");
	paramKeys.insert("heuristicMapping");
	paramKeys.insert("parameterizableCGRA");

	try
        {
          // try to access a nonexisting key
          for (auto itr : paramKeys)
          {
            param.at(itr);
          }
        }
        catch (json::out_of_range& e)
        {
          cout<<"Please include related parameter in param.json: "<<e.what()<<endl;
	        exit(0);
        }

        (*functionWithLoop)[param["kernel"]] = new list<int>();
        json loops = param["targetLoopsID"];
        for (int i=0; i<loops.size(); ++i) {
          // cout<<"add index "<<loops[i]<<endl;
          (*functionWithLoop)[param["kernel"]]->push_back(loops[i]);
        }

        // Configuration for customizable CGRA.
        rows                  = param["row"];
        columns               = param["column"];
        targetEntireFunction  = param["targetFunction"];
        targetNested          = param["targetNested"];
        doCGRAMapping         = param["doCGRAMapping"];
        isStaticElasticCGRA   = param["isStaticElasticCGRA"];
        isTrimmedDemo         = param["isTrimmedDemo"];
        ctrlMemConstraint     = param["ctrlMemConstraint"];
        bypassConstraint      = param["bypassConstraint"];
        regConstraint         = param["regConstraint"];
        precisionAware        = param["precisionAware"];
        diagonalVectorization = param["diagonalVectorization"];
        heterogeneity         = param["heterogeneity"];
        PathSupportDim        = param["PathSupportDim"];
        heuristicMapping      = param["heuristicMapping"];
        parameterizableCGRA   = param["parameterizableCGRA"];

        if (param.find("incrementalMapping") != param.end()) {
          incrementalMapping = param["incrementalMapping"];
	}
        if (param.find("supportDVFS") != param.end()) {
          supportDVFS = param["supportDVFS"];
	}
        if (param.find("DVFSAwareMapping") != param.end()) {
          DVFSAwareMapping = param["DVFSAwareMapping"];
	}
        if (param.find("DVFSIslandDim") != param.end()) {
          DVFSIslandDim = param["DVFSIslandDim"];
	}
        if (param.find("enablePowerGating") != param.end()) {
          enablePowerGating = param["enablePowerGating"];
	}
        if (param.find("vectorFactorForIdiv ") != param.end()) {
          vectorFactorForIdiv = param["vectorFactorForIdiv "];
        }
        if (param.find("testingOpcodeOffset") != param.end()) {
          testing_opcode_offset = param["testingOpcodeOffset"];
	}
        cout<<"Initialize opt latency for DFG nodes: "<<endl;
        for (auto& opt : param["optLatency"].items()) {
          cout<<opt.key()<<" : "<<opt.value()<<endl;
          (*execLatency)[opt.key()] = opt.value();
        }
        json pipeOpt = param["optPipelined"];
        for (int i=0; i<pipeOpt.size(); ++i) {
          pipelinedOpt->push_back(pipeOpt[i]);
        }
        cout<<"Initialize additional functionality on CGRA nodes: "<<endl;
        for (auto& opt : param["additionalFunc"].items()) {
          (*additionalFunc)[opt.key()] = new list<int>();
          cout<<opt.key()<<" : "<<opt.value()<<": ";
          for (int i=0; i<opt.value().size(); ++i) {
            (*additionalFunc)[opt.key()]->push_back(opt.value()[i]);
            cout<<opt.value()[i]<<" ";
          }
          cout<<endl;
        }
        cout<<"Finding fusion pattern for DFG: "<<endl;
        for (auto& opt : param["fusionPattern"].items()) {
          (*fusionPattern)[opt.key()] = new list<string>();
          cout<<opt.key()<<" : "<<opt.value()<<": ";
          for (int i=0; i<opt.value().size(); ++i) {
            (*fusionPattern)[opt.key()]->push_back(opt.value()[i]);
            cout<<opt.value()[i]<<" ";
          }
          cout<<endl;
        }
      }

      // Check existance.
      if (functionWithLoop->find(t_F.getName().str()) == functionWithLoop->end()) {
        cout<<"[function \'"<<t_F.getName().str()<<"\' is not in our target list]\n";
        return false;
      }
      cout << "==================================\n";
      cout<<"[function \'"<<t_F.getName().str()<<"\' is one of our targets]\n";

      list<Loop*>* targetLoops = getTargetLoops(t_F, functionWithLoop, targetNested);
      // TODO: will make a list of patterns/tiles to illustrate how the
      //       heterogeneity is
      DFG* dfg = new DFG(t_F, targetLoops, targetEntireFunction, precisionAware,
                         heterogeneity, execLatency, pipelinedOpt, fusionPattern, supportDVFS,
			 DVFSAwareMapping, vectorFactorForIdiv);
      CGRA* cgra = new CGRA(rows, columns, diagonalVectorization, heterogeneity,
		            parameterizableCGRA, additionalFunc, supportDVFS,
			    DVFSIslandDim);
      cgra->setRegConstraint(regConstraint);
      cgra->setCtrlMemConstraint(ctrlMemConstraint);
      cgra->setBypassConstraint(bypassConstraint);
      mapper = new Mapper(DVFSAwareMapping);

      // Show the count of different opcodes (IRs).
      cout << "==================================\n";
      cout << "[show opcode count]\n";
      dfg->showOpcodeDistribution();

      // Generate the DFG dot file.
      cout << "==================================\n";
      cout << "[generate dot for DFG]\n";
      dfg->generateDot(t_F, isTrimmedDemo);

      // Generate the DFG dot file.
      cout << "==================================\n";
      cout << "[generate JSON for DFG]\n";
      dfg->generateJSON();

      // Initialize the II.
      int ResMII = mapper->getResMII(dfg, cgra);
      cout << "==================================\n";
      cout << "[ResMII: " << ResMII << "]\n";
      int RecMII = mapper->getRecMII(dfg);
      cout << "==================================\n";
      cout << "[RecMII: " << RecMII << "]\n";
      int II = ResMII;
      if (II < RecMII)
        II = RecMII;

      if (supportDVFS) {
        dfg->initDVFSLatencyMultiple(II, DVFSIslandDim, cgra->getFUCount());
      }

      if (!doCGRAMapping) {
        cout << "==================================\n";
        return false;
      }
      // Heuristic algorithm (hill climbing) to get a valid mapping within
      // a acceptable II.
      bool success = false;
      if (!isStaticElasticCGRA) {
        cout << "==================================\n";
        typedef std::chrono::high_resolution_clock Clock;
        auto t1 = Clock::now();

        if (heuristicMapping) {
	  if(incrementalMapping){
            II = mapper->incrementalMap(cgra, dfg, II);
            cout << "[Incremental]\n";
	  }
	  else{
            cout << "[heuristic]\n";
            II = mapper->heuristicMap(cgra, dfg, II, isStaticElasticCGRA);
          }
        } else {
          cout << "[exhaustive]\n";
          II = mapper->exhaustiveMap(cgra, dfg, II, isStaticElasticCGRA);
        }

        auto t2 = Clock::now();
        int elapsedTime = std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count() / 1000000;
        std::cout <<"Mapping algorithm elapsed time="<<elapsedTime <<"ms"<< '\n';
      }

      // Partially exhaustive search to try to map the DFG onto
      // the static elastic CGRA.

      if (isStaticElasticCGRA and !success) {
        cout << "==================================\n";
        cout << "[exhaustive]\n";
        II = mapper->exhaustiveMap(cgra, dfg, II, isStaticElasticCGRA);
      }

      // Show the mapping and routing results with JSON output.
      if (II == -1)
        cout << "[fail]\n";
      else {
        mapper->showSchedule(cgra, dfg, II, isStaticElasticCGRA, parameterizableCGRA);
        cout << "[Mapping Success]\n";
        cout << "==================================\n";
        cout << "[Utilization & DVFS stats]\n";
        mapper->showUtilization(cgra, dfg, II, isStaticElasticCGRA, enablePowerGating);
        cout << "==================================\n";
        mapper->generateJSON(cgra, dfg, II, isStaticElasticCGRA);
	      cout << "[Output Json]\n";

	// save mapping results json file for possible incremental mapping
        if(!incrementalMapping) {
	        mapper->generateJSON4IncrementalMap(cgra, dfg);
          cout << "[Output Json for Incremental Mapping]\n";
        }
      }
      cout << "=================================="<<endl;

      return false;
    }

    /*
     * Add the loops of each kernel. Target nested-loops if it is indicated.
     */
    list<Loop*>* getTargetLoops(Function& t_F, map<string, list<int>*>* t_functionWithLoop, bool t_targetNested) {
      int targetLoopID = 0;
      list<Loop*>* targetLoops = new list<Loop*>();
      // Since the ordering of the target loop id could be random, I use O(n^2) to search the target loop.
      while((*t_functionWithLoop).at(t_F.getName().str())->size() > 0) {
        targetLoopID = (*t_functionWithLoop).at(t_F.getName().str())->front();
        (*t_functionWithLoop).at(t_F.getName().str())->pop_front();
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>().getLoopInfo();
        int tempLoopID = 0;
        Loop* current_loop = NULL;
        for(LoopInfo::iterator loopItr=LI.begin();
            loopItr!= LI.end(); ++loopItr) {
          // targetLoops->push_back(*loopItr);
          current_loop = *loopItr;
          if (tempLoopID == targetLoopID) {
            // Targets innermost loop if the param targetNested is not set.
            if (!t_targetNested) {
              while (!current_loop->getSubLoops().empty()) {
                errs()<<"[explore] nested loop ... subloop size: "<<current_loop->getSubLoops().size()<<"\n";
                // TODO: might change '0' to a reasonable index
                current_loop = current_loop->getSubLoops()[0];
              }
            }
            targetLoops->push_back(current_loop);
            errs()<<"*** reach target loop ID: "<<tempLoopID<<"\n";
            break;
          }
          ++tempLoopID;
        }
        if (targetLoops->size() == 0) {
          errs()<<"... no loop detected in the target kernel ...\n";
        }
      }
      errs()<<"... done detected loops.size(): "<<targetLoops->size()<<"\n";
      return targetLoops;
    }
  };
}

char mapperPass::ID = 0;
static RegisterPass<mapperPass> X("mapperPass", "DFG Pass Analyse", false, false);

/*
 * Add the kernel names of some popular applications.
 * Assume each kernel contains single loop.
 */
void addDefaultKernels(map<string, list<int>*>* t_functionWithLoop) {

  (*t_functionWithLoop)["_Z12ARENA_kerneliii"] = new list<int>();
  (*t_functionWithLoop)["_Z12ARENA_kerneliii"]->push_back(0);
  (*t_functionWithLoop)["_Z4spmviiPiS_S_"] = new list<int>();
  (*t_functionWithLoop)["_Z4spmviiPiS_S_"]->push_back(0);
  (*t_functionWithLoop)["_Z4spmvPiii"] = new list<int>();
  (*t_functionWithLoop)["_Z4spmvPiii"]->push_back(0);
  (*t_functionWithLoop)["adpcm_coder"] = new list<int>();
  (*t_functionWithLoop)["adpcm_coder"]->push_back(0);
  (*t_functionWithLoop)["adpcm_decoder"] = new list<int>();
  (*t_functionWithLoop)["adpcm_decoder"]->push_back(0);
  (*t_functionWithLoop)["kernel_gemm"] = new list<int>();
  (*t_functionWithLoop)["kernel_gemm"]->push_back(0);
  (*t_functionWithLoop)["kernel"] = new list<int>();
  (*t_functionWithLoop)["kernel"]->push_back(0);
  (*t_functionWithLoop)["_Z6kerneli"] = new list<int>();
  (*t_functionWithLoop)["_Z6kerneli"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfPi"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfPi"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_S_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_S_"]->push_back(0);
  (*t_functionWithLoop)["_Z6kerneliPPiS_S_S_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kerneliPPiS_S_S_"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPPii"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPPii"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelP7RGBType"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelP7RGBType"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelP7RGBTypePi"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelP7RGBTypePi"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelP7RGBTypeP4Vect"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelP7RGBTypeP4Vect"]->push_back(0);
  (*t_functionWithLoop)["fir"] = new list<int>();
  (*t_functionWithLoop)["fir"]->push_back(0);
  (*t_functionWithLoop)["spmv"] = new list<int>();
  (*t_functionWithLoop)["spmv"]->push_back(0);
  // (*functionWithLoop)["fir"].push_back(1);
  (*t_functionWithLoop)["latnrm"] = new list<int>();
  (*t_functionWithLoop)["latnrm"]->push_back(1);
  (*t_functionWithLoop)["fft"] = new list<int>();
  (*t_functionWithLoop)["fft"]->push_back(0);
  (*t_functionWithLoop)["BF_encrypt"] = new list<int>();
  (*t_functionWithLoop)["BF_encrypt"]->push_back(0);
  (*t_functionWithLoop)["susan_smoothing"] = new list<int>();
  (*t_functionWithLoop)["susan_smoothing"]->push_back(0);

  (*t_functionWithLoop)["_Z9LUPSolve0PPdPiS_iS_"] = new list<int>();
  (*t_functionWithLoop)["_Z9LUPSolve0PPdPiS_iS_"]->push_back(0);

  // For LU:
  // init
  (*t_functionWithLoop)["_Z6kernelPPdidPi"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPPdidPi"]->push_back(0);

  // solver0 & solver1
  (*t_functionWithLoop)["_Z6kernelPPdPiS_iS_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPPdPiS_iS_"]->push_back(0);

  // determinant
  (*t_functionWithLoop)["_Z6kernelPPdPii"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPPdPii"]->push_back(0);

  // invert
  (*t_functionWithLoop)["_Z6kernelPPdPiiS0_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPPdPiiS0_"]->push_back(0);

  // nested
  // (*t_functionWithLoop)["_Z6kernelPfS_S_"] = new list<int>();
  // (*t_functionWithLoop)["_Z6kernelPfS_S_"]->push_back(0);

  (*t_functionWithLoop)["_Z6kernelPiS_i"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPiS_i"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_f"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_f"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPiS_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPiS_"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_ff"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_ff"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPiS_ii"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPiS_ii"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPfS_if"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPfS_if"]->push_back(0);
  (*t_functionWithLoop)["_Z6kernelPiS_S_"] = new list<int>();
  (*t_functionWithLoop)["_Z6kernelPiS_S_"]->push_back(0);
}


