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
#include "json.hpp"
#include "Mapper.h"

using namespace llvm;
using namespace std;
using json = nlohmann::json;

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

      // Read the parameter JSON file.
      ifstream i("../arch/arch.json");
      json param;
      i >> param;
 
      // Set the target function and loop.
      map<string, list<int>*>* functionWithLoop = new map<string, list<int>*>();
      addDefaultKernels(functionWithLoop);

      (*functionWithLoop)[param["kernel"]] = new list<int>();
      json loops = param["targetLoopsID"];
      for (int i=0; i<loops.size(); ++i) {
        cout<<"add index "<<loops[i]<<endl;
        (*functionWithLoop)[param["kernel"]]->push_back(loops[i]);
      }

      // Configuration for static CGRA.
      // int rows = 8;
      // int columns = 8;
      // bool isStaticElasticCGRA = true;
      // bool isTrimmedDemo = true;
      // int ctrlMemConstraint = 1;
      // int bypassConstraint = 3;
      // int regConstraint = 1;
     
      // Configuration for dynamic CGRA.
      int rows                 = param["row"];
      int columns              = param["column"];
      bool isStaticElasticCGRA = param["isStaticElasticCGRA"];
      bool isTrimmedDemo       = param["isTrimmedDemo"];
      int ctrlMemConstraint    = param["ctrlMemConstraint"];
      int bypassConstraint     = param["bypassConstraint"];
      // FIXME: should not change this for now, it is the four directions by default
      int regConstraint        = param["regConstraint"];
      bool heterogeneity       = param["heterogeneity"];

      // Check existance.
      if (functionWithLoop->find(t_F.getName().str()) == functionWithLoop->end()) {
        errs()<<"[function \'"<<t_F.getName()<<"\' is not in our target list]\n";
        return false;
      }
      errs() << "==================================\n";
      errs()<<"[function \'"<<t_F.getName()<<"\' is one of our targets]\n";

      list<Loop*>* targetLoops = getTargetLoops(t_F, functionWithLoop, param["targetNested"]);
      // TODO: will make a list of patterns/tiles to illustrate how the
      //       heterogeneity is
      DFG* dfg = new DFG(t_F, targetLoops, heterogeneity);
      CGRA* cgra = new CGRA(rows, columns, heterogeneity);
      cgra->setRegConstraint(regConstraint);
      cgra->setCtrlMemConstraint(ctrlMemConstraint);
      cgra->setBypassConstraint(bypassConstraint);
      mapper = new Mapper();

      // Show the count of different opcodes (IRs).
      errs() << "==================================\n";
      errs() << "[show opcode count]\n";
      dfg->showOpcodeDistribution();

      // Generate the DFG dot file.
      errs() << "==================================\n";
      errs() << "[generate dot for DFG]\n";
      dfg->generateDot(t_F, isTrimmedDemo);

      // Generate the DFG dot file.
      errs() << "==================================\n";
      errs() << "[generate JSON for DFG]\n";
      dfg->generateJSON();

      // Initialize the II.
      int ResMII = mapper->getResMII(dfg, cgra);
      errs() << "==================================\n";
      errs() << "[ResMII: " << ResMII << "]\n";
      int RecMII = mapper->getRecMII(dfg);
      errs() << "==================================\n";
      errs() << "[RecMII: " << RecMII << "]\n";
      int II = ResMII;
      if(II < RecMII)
        II = RecMII;
      
      // Heuristic algorithm (hill climbing) to get a valid mapping within
      // a acceptable II.
      bool success = false;
      if (!isStaticElasticCGRA) {
        errs() << "==================================\n";
        errs() << "[heuristic]\n";
        II = mapper->heuristicMap(cgra, dfg, II, isStaticElasticCGRA);
      }

      // Partially exhaustive search to try to map the DFG onto
      // the static elastic CGRA.

      if (isStaticElasticCGRA and !success) {
        errs() << "==================================\n";
        errs() << "[exhaustive]\n";
        II = mapper->exhaustiveMap(cgra, dfg, II, isStaticElasticCGRA);
      }

      // Show the mapping and routing results with JSON output.
      if (II == -1)
        errs() << "[fail]\n";
      else {
        mapper->showSchedule(cgra, dfg, II, isStaticElasticCGRA);
        errs() << "==================================\n";
        errs() << "[success]\n";
        errs() << "==================================\n";
        mapper->generateJSON(cgra, dfg, II, isStaticElasticCGRA);
        errs() << "[Output Json]\n";
      }
      errs() << "==================================\n";

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
}


