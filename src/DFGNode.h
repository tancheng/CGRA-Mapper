/*
 * ======================================================================
 * DFGNode.h
 * ======================================================================
 * DFG node implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 19, 2019
 */

#ifndef DFGNode_H
#define DFGNode_H

#include <llvm/IR/Value.h>
#include <llvm/IR/Constants.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Instructions.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/IR/BasicBlock.h>

#include <string>
#include <list>
#include <stdio.h>
#include <iostream>

#include "DFGEdge.h"
#define MAXIMUM_COMBINED_TYPE 100

using namespace llvm;
using namespace std;

class DFGEdge;

class DFGNode {
  private:
    // Original id that is ordered in the original execution order (i.e.,
    // CPU/IR execution sequential ordering).
    int m_id;
    bool m_precisionAware;
    Instruction* m_inst;
    Value* m_value;
    StringRef m_stringRef;
    string m_opcodeName;
    // m_pathName is derived from basic block of llvm
    string m_pathName;  
    list<DFGEdge*> m_inEdges;
    list<DFGEdge*> m_outEdges;
    list<DFGNode*>* m_succNodes;
    list<DFGNode*>* m_predNodes;
    list<DFGNode*>* m_patternNodes;
    list<int>* m_cycleID;
    bool m_isMapped;
    int m_numConst;
    string m_optType;
    string m_fuType;
    bool m_combined;
    // Used for specialized fusion (e.g. alu+mul and icmp+br can be regared as two kinds of complex nodes, so there are different tiles to support them)
    string m_combinedtype;
    bool m_isPatternRoot;
    bool m_critical;
    int m_level;
    int m_execLatency;
    bool m_pipelinable;
    // "m_predicated" indicates whether the execution of the node depends on
    // predication or not (i.e., the predecessor probably is a "branch"). 
    bool m_isPredicatee;
    list<DFGNode*>* m_predicatees;
    bool m_isPredicater;
    DFGNode* m_patternRoot;
    void setPatternRoot(DFGNode*);

    int m_DVFSLatencyMultiple;
    bool m_supportDVFS;

    // "m_bbID" is used to specify which basicblock is this DFGNode in.
    int m_bbID;

  public:
    DFGNode(int, bool, Instruction*, StringRef, bool);
    DFGNode(int, DFGNode* old_node);
    int getID();
    void setID(int);
    void setLevel(int);
    int getLevel();
    bool isMapped();
    void setMapped();
    void clearMapped();
    bool isLoad();
    bool isStore();
    bool isReturn();
    string isCall();
    bool isBranch();
    bool isPhi();
    bool isAddSub();
    bool isScalarAddSub();
    bool isConstantAddSub();
    // Detect integer addition.
    bool isIaddIsub();
    bool isMul();
    bool isCmp();
    bool isBitcast();
    bool isGetptr();
    bool isSel();
    bool isMAC();
    bool isLogic();
    bool isOpt(string);
    bool isVectorized();
    // Detect division.
    bool isDiv();
    string getComplexType();
    bool hasCombined();
    void setCombine(string type="");
    void addPatternPartner(DFGNode*);
    Instruction* getInst();
    StringRef getStringRef();
    string getOpcodeName();
    string getPathName();
    list<DFGNode*>* getPredNodes();
    list<DFGNode*>* getSuccNodes();
    void deleteSuccNode(DFGNode*);
    void deletePredNode(DFGNode*);
    void deleteAllSuccNodes();
    void deleteAllPredNodes();
    void addSuccNode(DFGNode*);
    void addPredNode(DFGNode*);
    bool isSuccessorOf(DFGNode*);
    bool isPredecessorOf(DFGNode*);
    bool isOneOfThem(list<DFGNode*>*);
    void setInEdge(DFGEdge*);
    void setOutEdge(DFGEdge*);
    void cutEdges();
    string getJSONOpt();
    string getFuType();
    void addConst();
    void removeConst();
    int getNumConst();
    void initType();
    bool isPatternRoot();
    DFGNode* getPatternRoot();
    list<DFGNode*>* getPatternNodes();
    void setCritical();
    void addCycleID(int);
    bool isCritical();
    int getCycleID();
    list<int>* getCycleIDs();
    void addPredicatee(DFGNode*);
    list<DFGNode*>* getPredicatees();
    void setPredicatee();
    bool isPredicatee();
    bool isPredicater();
    bool shareSameCycle(DFGNode*);
    void setExecLatency(int);
    bool isMultiCycleExec(int);
    int getExecLatency(int);
    void setPipelinable();
    bool isPipelinable();
    bool shareFU(DFGNode*);
    void setDVFSLatencyMultiple(int);
    int getDVFSLatencyMultiple();

    // Sets m_bbID.
    void setBBID(int);

    // Reads m_bbID.
    int getBBID();

};

#endif
