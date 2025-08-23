/*
 * ======================================================================
 * CGRA.h
 * ======================================================================
 * CGRA implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

//#include "llvm/Pass.h"
#include "CGRANode.h"
#include "CGRALink.h"
#include <iostream>
//#include <llvm/Support/raw_ostream.h>

using namespace llvm;

class CGRA {
  private:
    int m_FUCount;
    int m_LinkCount;
    int m_rows;
    int m_columns;
    bool m_supportDVFS;
    bool m_supportInclusive;
    int m_DVFSIslandDim;
    map<int, vector<CGRANode*>> m_DVFSIslands;
    list<string>* m_supportComplex;
    list<string>* m_supportCall;
    void disableSpecificConnections();

  public:
    CGRA(int, int, std::string, list<string>*, bool, map<string, list<int>*>*, bool, int, bool=true);
    CGRANode ***nodes;
    CGRALink **links;
    int getFUCount();
    int getLinkCount();
    void getRoutingResource();
    void constructMRRG(int);
    int getRows() { return m_rows; }
    int getColumns() { return m_columns; }
    CGRALink* getLink(CGRANode*, CGRANode*);
    void setBypassConstraint(int);
    void setCtrlMemConstraint(int);
    void setRegConstraint(int);
    map<int, vector<CGRANode*>> getDVFSIslands();
    // Aligns all the CGRA nodes within the same DVFS island to the
    // same DVFS level based on the DVFS level of the given CGRA node.
    void syncDVFSIsland(CGRANode*);
    list<string>* getSupportComplex();
    list<string>* getSupportCall();
    bool getSupportInclusive();
};

