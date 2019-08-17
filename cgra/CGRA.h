/*
 * ======================================================================
 * CGRA.h
 * ======================================================================
 * CGRA implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "llvm/Pass.h"
#include "CGRANode.h"
#include "CGRALink.h"
#include <llvm/Support/raw_ostream.h>

#define REG_COUNT 2
#define CTRL_MEM_SIZE 20

using namespace llvm;

class CGRA
{
  private:
    int FUCount;
    int LinkCount;
    int rows;
    int columns;

  public:
    CGRA(int, int);
    CGRANode ***nodes;
    CGRALink **links;
    int getFUCount();
    void getRoutingResource();
    void constructMRRG(int);
    int getRows(){ return rows; }
    int getColumns(){ return columns; }
    CGRALink* getLink(CGRANode*, CGRANode*);
};
