/*
 * ======================================================================
 * cgraPass.cpp
 * ======================================================================
 * CGRA pass implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include <llvm/IR/Function.h>
#include <llvm/Pass.h>
#include <llvm/Analysis/LoopInfo.h>
#include <llvm/Analysis/LoopIterator.h>
#include <stdio.h>
#include "Mapper.h"

using namespace llvm;

namespace {

//  typedef pair<Value*, StringRef> DFGNode;
//  typedef pair<DFGNode, DFGNode> DFGEdge;
  struct cgraPass : public FunctionPass {

  public:
    static char ID;
    Mapper* mapper;
    cgraPass() : FunctionPass(ID) {}

    void getAnalysisUsage(AnalysisUsage &AU) const override {
      AU.addRequired<LoopInfoWrapperPass>();
      AU.addPreserved<LoopInfoWrapperPass>();
      AU.setPreservesAll();
    }

    bool runOnFunction(Function &t_F) override {

      // Set the target function and loop.
      map<string, int>* functionWithLoop = new map<string, int>();
      (*functionWithLoop)["fir"] = 0;
      (*functionWithLoop)["latnrm"] = 1;
      (*functionWithLoop)["fft"] = 0;
      (*functionWithLoop)["BF_encrypt"] = 0;
      (*functionWithLoop)["susan_smoothing"] = 0;

      // Configuration for static CGRA.
      // int rows = 8;
      // int columns = 8;
      // bool isStaticElasticCGRA = true;
      // bool isTrimmedDemo = true;
      // int ctrlMemConstraint = 1;
      // int bypassConstraint = 3;
      // int regConstraint = 1;

      // Configuration for dynamic CGRA.
      int rows = 4;
      int columns = 4;
      bool isStaticElasticCGRA = false;
      bool isTrimmedDemo = true;
      int ctrlMemConstraint = 100;
      int bypassConstraint = 4;
      int regConstraint = 1;

      if (functionWithLoop->find(t_F.getName()) == functionWithLoop->end()) {
        errs()<<"[target function \'"<<t_F.getName()<<"\' is not detected]\n";
        return false;
      }
      errs() << "==================================\n";
      errs()<<"[target function \'"<<t_F.getName()<<"\' is detected]\n";

      Loop* targetLoop = getTargetLoop(t_F, functionWithLoop);
      DFG* dfg = new DFG(t_F, targetLoop);
      CGRA* cgra = new CGRA(rows, columns);
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
        success = mapper->heuristicMap(cgra, dfg, II, isStaticElasticCGRA);
      }

      // Partially exhaustive search to try to map the DFG onto
      // the static elastic CGRA.

      if (isStaticElasticCGRA and !success) {
        errs() << "==================================\n";
        errs() << "[exhaustive]\n";
        success = mapper->exhaustiveMap(cgra, dfg, II, isStaticElasticCGRA);
      }

      // Show the mapping and routing results with JSON output.
      if (!success)
        errs() << "[fail]\n";
      else {
        mapper->showSchedule(cgra, dfg, II, isStaticElasticCGRA);
        errs() << "==================================\n";
        errs() << "[success]\n";
        errs() << "==================================\n";
        mapper->writeJSON(cgra, dfg, II, isStaticElasticCGRA);
        errs() << "[Output Json]\n";
      }
      errs() << "==================================\n";

      return false;
    }


    Loop* getTargetLoop(Function& t_F, map<string, int>* t_functionWithLoop) {
      int targetLoopID = 0;
      targetLoopID = (*t_functionWithLoop)[t_F.getName()];

      // Specify the particular loop we are focusing on.
      // TODO: move the following to another .cpp file.
      LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>().getLoopInfo();
      Loop* targetLoop = NULL;
      int tempLoopID = 0;
      for(LoopInfo::iterator loopItr=LI.begin();
          loopItr!= LI.end(); ++loopItr) {
        targetLoop = *loopItr;
        if (tempLoopID == targetLoopID) {
          while (!targetLoop->getSubLoops().empty()) {
            errs()<<"*** detected nested loop ... size: "<<targetLoop->getSubLoops().size()<<"\n";
            // TODO: might change '0' to a reasonable index
            targetLoop = targetLoop->getSubLoops()[0];
          }
          errs()<<"*** reach target loop ID: "<<tempLoopID<<"\n";
          break;
        }
        ++tempLoopID;
      }
      if (targetLoop == NULL) {
        errs()<<"... no loop detected in the target kernel ...\n";
      }
      return targetLoop;
    }

  };
}

char cgraPass::ID = 0;
static RegisterPass<cgraPass> X("cgraPass", "DFG Pass Analyse", false, false);
