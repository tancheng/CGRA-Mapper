/*
 * ======================================================================
 * CGRANode.cpp
 * ======================================================================
 * CGRA tile implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "CGRANode.h"
#include <stdio.h>

#define SINGLE_OCCUPY     0 // A single-cycle opt is in the FU
#define START_PIPE_OCCUPY 1 // A multi-cycle opt starts in the FU
#define END_PIPE_OCCUPY   2 // A multi-cycle opt ends in the FU
#define IN_PIPE_OCCUPY    3 // A multi-cycle opt is occupying the FU

//CGRANode::CGRANode(int t_id) {
//  m_id = t_id;
//  m_currentCtrlMemItems = 0;
//  m_canStore = false;
//  m_canLoad = false;
//}

CGRANode::CGRANode(int t_id, int t_x, int t_y) {
  m_id = t_id;
  m_currentCtrlMemItems = 0;
  m_disabled = false;
  m_canStore = false;
  m_canLoad = false;
  m_supportComplex = false;
  m_supportComplexType = vector<string>();
  // It's not necessary to support specific function on each tile.
  m_canCall = vector<string>();

  m_x = t_x;
  m_y = t_y;
  m_neighbors = NULL;
  m_occupiableInLinks = NULL;
  m_occupiableOutLinks = NULL;
  m_regs_duration = NULL;
  m_regs_timing = NULL;

  // used for parameterizable CGRA functional units
  m_canAdd    = true;
  m_canMul    = true;
  m_canShift  = true;
  m_canPhi    = true;
  m_canSel    = true;
  m_canCmp    = true;
  m_canMAC    = true;
  m_canLogic  = true;
  m_canBr     = true;
  m_canReturn = true;

  // supportDVFS should be leveraged with the optLatency (i.e., multi-
  // cycle execution) to mimic the operations running on the low
  // frequency.
  m_supportDVFS = false;

  // Indicates whether this CGRA node has already been mapped
  // with at least one operation.
  m_mapped = false;
  m_DVFSLatencyMultiple = 1;
  m_synced = false;

  // Indicates whether this CGRA node can execute multiple operations
  // simultaneously. (e.g.,  single-cycle overlaps with multi-cycle)
  // i.e., inclusive execution
  m_canMultipleOps = true;
}

// FIXME: should handle the case that the data is maintained in the registers
//        for multiple cycles.
void CGRANode::allocateReg(CGRALink* t_link, int t_cycle, int t_duration, int t_II) {
  int reg_id = t_link->getDirectionID(this);
  allocateReg(reg_id, t_cycle, t_duration, t_II);
}

void CGRANode::allocateReg(int t_port_id, int t_cycle, int t_duration, int t_II) {
  bool allocated = false;
  for (int i=0; i<m_registerCount; ++i) {
    bool reg_occupied = false;
    for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
      for (int d=0; d<t_duration; ++d) {
        if (cycle+d<m_cycleBoundary and m_regs_duration[cycle+d][i] != -1)
          reg_occupied = true;
      }
    }
    for (int cycle=t_cycle; cycle>=0; cycle-=t_II) {
      for (int d=0; d<t_duration; ++d) {
        if (m_regs_duration[cycle+d][i] != -1)
          reg_occupied = true;
      }
    }
    if (reg_occupied == false) {
      cout<<"[DEBUG] in allocateReg() t_cycle: "<<t_cycle<<"; i: "<<i<<" CGRA node: "<<this->getID()<<"; link: "<<t_port_id<<" duration "<<t_duration<<"\n";
      for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
        m_regs_timing[cycle][i] = t_port_id;
        for (int d=0; d<t_duration; ++d) {
          if (cycle+d<m_cycleBoundary) {
            // assert(m_regs_duration[cycle+d][i] == -1);
            m_regs_duration[cycle+d][i] = t_port_id;
          }
        }
      }
      for (int cycle=t_cycle; cycle>=0; cycle-=t_II) {
        m_regs_timing[cycle][i] = t_port_id;
        for (int d=0; d<t_duration; ++d) {
          m_regs_duration[cycle+d][i] = t_port_id;
        }
      }
      allocated = true;
      break;
    }
  }
  cout<<"[DEBUG] done reg allocation"<<endl;
  //assert(allocated);
}

int* CGRANode::getRegsAllocation(int t_cycle) {
  return m_regs_timing[t_cycle];
}

void CGRANode::setCtrlMemConstraint(int t_ctrlMemConstraint) {
  m_ctrlMemSize = t_ctrlMemConstraint;
}

void CGRANode::setRegConstraint(int t_registerConstraint) {
  m_registerCount = t_registerConstraint;
}

void CGRANode::setID(int t_id) {
  m_id = t_id;
}

void CGRANode::setLocation(int t_x, int t_y) {
  m_x = t_x;
  m_y = t_y;
}

void CGRANode::enableDVFS() {
  m_supportDVFS = true;
}

bool CGRANode::isDVFSEnabled() {
  return m_supportDVFS;
}

void CGRANode::setDVFSIsland(int t_x, int t_y, int t_id) {
  m_DVFSIslandX = t_x;
  m_DVFSIslandY = t_y;
  m_DVFSIslandId = t_id;
}

int CGRANode::getDVFSIslandX() {
  return m_DVFSIslandX;
}

int CGRANode::getDVFSIslandY() {
  return m_DVFSIslandY;
}

int CGRANode::getDVFSIslandID() {
  return m_DVFSIslandId;
}

void CGRANode::setDVFSLatencyMultiple(int t_DVFSLatencyMultiple) {
  assert(t_DVFSLatencyMultiple == 1 || t_DVFSLatencyMultiple == 2 || t_DVFSLatencyMultiple == 4);
  m_DVFSLatencyMultiple = t_DVFSLatencyMultiple;
}

bool CGRANode::isFrequencyLowered() {
  return (m_DVFSLatencyMultiple != 1);
}

int CGRANode::getDVFSLatencyMultiple() {
  return m_DVFSLatencyMultiple;
}

int CGRANode::getID() {
  return m_id;
}

void CGRANode::attachInLink(CGRALink* t_link) {
  m_inLinks.push_back(t_link);
}

void CGRANode::attachOutLink(CGRALink* t_link) {
  m_outLinks.push_back(t_link);
}

list<CGRALink*>* CGRANode::getInLinks() {
  return &m_inLinks;
}

list<CGRALink*>* CGRANode::getOutLinks() {
  return &m_outLinks;
}

list<CGRANode*>* CGRANode::getNeighbors() {
  if (m_neighbors != NULL)
    return m_neighbors;
  m_neighbors = new list<CGRANode*>();
  for (CGRALink* link: m_outLinks)
    m_neighbors->push_back(link->getConnectedNode(this));
  return m_neighbors;
}

void CGRANode::constructMRRG(int t_CGRANodeCount, int t_II) {
  m_cycleBoundary = t_CGRANodeCount*t_II*t_II;
  m_currentCtrlMemItems = 0;
  m_registers.clear();
  // Delete all these local arrays to avoid memory leakage.
  if (m_dfgNodesWithOccupyStatus.size() > 0) {
    for (list<pair<DFGNode*, int>>* opts: m_dfgNodesWithOccupyStatus) {
      opts->clear();
    }
  }
  m_dfgNodesWithOccupyStatus.clear();
  // m_dfgNodesWithOccupyStatus = new list<list<pair<DFGNode*, int>>*>();
  for (int i=0; i<m_cycleBoundary; ++i) {
    m_dfgNodesWithOccupyStatus.push_back(new list<pair<DFGNode*, int>>());
  }

  m_regs_duration = new int*[m_cycleBoundary];
  m_regs_timing = new int*[m_cycleBoundary];
  for (int i=0; i<m_cycleBoundary; ++i) {
    m_regs_duration[i] = new int[m_registerCount];
    m_regs_timing[i] = new int[m_registerCount];
    for (int j=0; j<m_registerCount; ++j) {
      m_regs_duration[i][j] = -1;
      m_regs_timing[i][j] = -1;
    }
  }
}

bool CGRANode::canSupport(DFGNode* t_opt) {
  if (m_disabled)
    return false;
  // Check whether this CGRA node supports the required functionality.
  string call_f = t_opt->isCall();
  if (call_f.compare("None") && !canCall(call_f)) {
    return false;
  }
  string complex_f = t_opt->getComplexType();
  if (complex_f.compare("None") && !supportComplex(complex_f)) {
    return false;
  }
  if ((t_opt->isLoad()       and !canLoad())  or
      (t_opt->isStore()      and !canStore()) or
      (t_opt->isReturn()     and !canReturn()) or
      (t_opt->isVectorized() and !supportVectorization()) or
      (t_opt->isAddSub()     and !canAdd()) or  // We assume the HW adder can do both add and sub.
      (t_opt->isMul()        and !canMul()) or
      (t_opt->isPhi()        and !canPhi()) or
      (t_opt->isSel()        and !canSel()) or
      (t_opt->isMAC()        and !canMAC()) or
      (t_opt->isLogic()      and !canLogic()) or
      (t_opt->isBranch()     and !canBr()) or
      (t_opt->isCmp()        and !canCmp()) or
      (t_opt->isDiv()        and !canDiv())
      ) {
    return false;
  }
  return true;
}

bool CGRANode::canOccupy(DFGNode* t_opt, int t_cycle, int t_II) {
  if (m_disabled)
    return false;

  // Check whether this CGRA node supports the required functionality.
  if (!canSupport(t_opt)) {
    return false;
  }

  // Check whether the limit of config mem is reached.
  if (m_currentCtrlMemItems + 1 > m_ctrlMemSize) {
    return false;
  }

  // Handles DVFS-based execution.
  if (isDVFSEnabled()) {
    if (t_opt->getDVFSLatencyMultiple() < getDVFSLatencyMultiple()) {
      // Cannot occupy if the operation required DVFS frequency is higher
      // than the available one in tile. Note that DVFSLatencyMultile as 1
      // indicates the highest frequency.
      return false;
    }
    if (getDVFSLatencyMultiple() > 1 and t_cycle%t_II%getDVFSLatencyMultiple() != 0) {
      return false;
    }
  }

  // Handle multi-cycle execution and pipelinable operations.
  if (not t_opt->isMultiCycleExec(getDVFSLatencyMultiple())) {
    // Single-cycle opt:
    for (int cycle=t_cycle%t_II; cycle<m_cycleBoundary; cycle+=t_II) {
      // If this tile don't support inclusive execution (canMultipleOps() == false), and there has been an operation occupied this tile at the current cycle, we cannot map t_opt on it. 
      if (!canMultipleOps() && !m_dfgNodesWithOccupyStatus[cycle]->empty()) {
        return false;
      }
      for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
        if (p.second != IN_PIPE_OCCUPY) {
          return false;
        }
      }
    }
  } else {
    // Multi-cycle opt.
    for (int cycle=t_cycle%t_II; cycle<m_cycleBoundary; cycle+=t_II) {
      // Can not support simultaneous execution of multiple operations.
      if (!canMultipleOps()) {
        int exec_latency = t_opt->getExecLatency(getDVFSLatencyMultiple());
        for (int duration=0; duration < exec_latency; duration++) {
          if (cycle + duration >= m_cycleBoundary) {
            break;
          }
          if (!m_dfgNodesWithOccupyStatus[cycle+duration]->empty()) {
            return false;
          }
        }
      }
      else {
        // Check start cycle.
        for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
          // Cannot occupy/overlap by/with other operation if DVFS is enabled.
          if (isDVFSEnabled() and
              (p.second == SINGLE_OCCUPY or
              p.second == START_PIPE_OCCUPY or
              p.second == IN_PIPE_OCCUPY or
              p.second == END_PIPE_OCCUPY)) {
            return false;
          }
          // Multi-cycle opt's start cycle overlaps with single-cycle opt' cycle.
          else if (p.second == SINGLE_OCCUPY) {
            return false;
          }
          // Multi-cycle opt's start cycle overlaps with multi-cycle opt's start cycle.
          else if (p.second == START_PIPE_OCCUPY) {
            return false;
          }
          // Multi-cycle opt's start cycle overlaps with multi-cycle opt with the same type:
          else if ((p.second == IN_PIPE_OCCUPY or p.second == END_PIPE_OCCUPY) and
                  (t_opt->shareFU(p.first))   and
                  (not t_opt->isPipelinable() or not p.first->isPipelinable())) {
            return false;
          }
        }
        if (cycle+t_opt->getExecLatency(getDVFSLatencyMultiple())-1 >= m_cycleBoundary) {
          break;
        }
        // Check end cycle.
        for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle+t_opt->getExecLatency(getDVFSLatencyMultiple())-1])) {
          // Multi-cycle opt's end cycle overlaps with single-cycle opt' cycle.
          if (p.second == SINGLE_OCCUPY) {
            return false;
          }
          // Multi-cycle opt's end cycle overlaps with multi-cycle opt's end cycle.
          else if (p.second == END_PIPE_OCCUPY) {
            return false;
          }
          // Multi-cycle opt's end cycle overlaps with multi-cycle opt with the same type:
          else if ((p.second == IN_PIPE_OCCUPY or p.second == START_PIPE_OCCUPY) and
                  (t_opt->shareFU(p.first))   and
                  (not t_opt->isPipelinable() or not p.first->isPipelinable())) {
            return false;
          }
        }
      }
    }
  }

  return true;
}

bool CGRANode::isOccupied(int t_cycle, int t_II) {
  for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
    for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
      // If DVFS is supported, the entire tile is occupied before the current multi-cycle operation
      // completes. Otherwise, the next operation can start before the current one completes.
      if (p.second == START_PIPE_OCCUPY or p.second == SINGLE_OCCUPY or m_supportDVFS) {
        return true;
      }
    }
  }
  return false;
}

bool CGRANode::isStartOrInPipe(int t_cycle, int t_II) {
  for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
    for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
      if (p.second == START_PIPE_OCCUPY or p.second == IN_PIPE_OCCUPY) {
        return true;
      }
    }
  }
  return false;
}

bool CGRANode::isInOrEndPipe(int t_cycle, int t_II) {
  for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
    for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
      if (p.second == IN_PIPE_OCCUPY or p.second == END_PIPE_OCCUPY) {
        return true;
      }
    }
  }
  return false;
}

bool CGRANode::isEndPipe(int t_cycle, int t_II) {
  for (int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=t_II) {
    for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[cycle])) {
      if (p.second == END_PIPE_OCCUPY) {
        return true;
      }
    }
  }
  return false;
}

bool CGRANode::isSynced() {
  return m_synced;
}

void CGRANode::syncDVFS() {
  m_synced = true;
}

bool CGRANode::isMapped() {
  return m_mapped;
}

void CGRANode::setDFGNode(DFGNode* t_opt, int t_cycle, int t_II,
    bool t_isStaticElasticCGRA) {
  int interval = t_II;
  if (t_isStaticElasticCGRA) {
    interval = 1;
  }
  m_mapped = true;
  if (isDVFSEnabled()) {
    if (not m_synced) {
      setDVFSLatencyMultiple(t_opt->getDVFSLatencyMultiple());
    }
  }
  for (int cycle=t_cycle%interval; cycle<m_cycleBoundary; cycle+=interval) {
    if (not t_opt->isMultiCycleExec(getDVFSLatencyMultiple())) {
      m_dfgNodesWithOccupyStatus[cycle]->push_back(make_pair(t_opt, SINGLE_OCCUPY));
    } else {
      m_dfgNodesWithOccupyStatus[cycle]->push_back(make_pair(t_opt, START_PIPE_OCCUPY));
      for (int i=1; i<t_opt->getExecLatency(getDVFSLatencyMultiple())-1; ++i) {
        if (cycle+i < m_cycleBoundary) {
          m_dfgNodesWithOccupyStatus[cycle+i]->push_back(make_pair(t_opt, IN_PIPE_OCCUPY));
        }
      }
      int lastCycle = cycle+t_opt->getExecLatency(getDVFSLatencyMultiple())-1;
      if (lastCycle < m_cycleBoundary) {
        m_dfgNodesWithOccupyStatus[lastCycle]->push_back(make_pair(t_opt, END_PIPE_OCCUPY));
      }
    }
  }

  cout<<"[DEBUG] setDFGNode "<<t_opt->getID()<<" onto CGRANode "<<getID()<<" at cycle: "<<t_cycle<<"\n";
  ++m_currentCtrlMemItems;
  t_opt->setMapped();
}

DFGNode* CGRANode::getMappedDFGNode(int t_cycle) {
  for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[t_cycle])) {
    if (p.second == SINGLE_OCCUPY or p.second == END_PIPE_OCCUPY) {
      return p.first;
    }
  }
  return NULL;
}

bool CGRANode::containMappedDFGNode(DFGNode* t_node, int t_II) {
  for (int c=0; c<2*t_II; ++c) {
    for (pair<DFGNode*, int> p: *(m_dfgNodesWithOccupyStatus[c])) {
      if (t_node == p.first) {
        return true;
      }
    }
  }
  return false;
}

void CGRANode::configXbar(CGRALink*, int, int)
{

}

void CGRANode::addRegisterValue(float t_value) {
  m_registers.push_back(t_value);
}

list<CGRALink*>* CGRANode::getOccupiableInLinks(int t_cycle, int t_II) {
  if (m_occupiableInLinks == NULL)
    m_occupiableInLinks = new list<CGRALink*>();
  m_occupiableInLinks->clear();
  for (CGRALink* link: m_inLinks) {
    if (link->canOccupy(t_cycle, t_II)) {
      m_occupiableInLinks->push_back(link);
    }
  }
  return m_occupiableInLinks;
}

list<CGRALink*>* CGRANode::getOccupiableOutLinks(int t_cycle, int t_II) {
  if (m_occupiableOutLinks == NULL)
    m_occupiableOutLinks = new list<CGRALink*>();
  m_occupiableOutLinks->clear();
  for (CGRALink* link: m_outLinks) {
    if (link->canOccupy(t_cycle, t_II)) {
      m_occupiableOutLinks->push_back(link);
    }
  }
  return m_occupiableOutLinks;
}

int CGRANode::getAvailableRegisterCount() {
  return (m_registerCount - m_registers.size());
}

CGRALink* CGRANode::getInLink(CGRANode* t_node) {
  for (CGRALink* link: m_inLinks) {
    if (link->getSrc() == t_node) {
      return link;
    }
  }
  // will definitely return one inlink
  assert(0);
}

CGRALink* CGRANode::getOutLink(CGRANode* t_node) {
  for (CGRALink* link: m_outLinks) {
    if (link->getDst() == t_node)
      return link;
  }
  return NULL;
  // will definitely return one outlink
//  assert(0);
}

int CGRANode::getMinIdleCycle(DFGNode* t_dfgNode, int t_cycle, int t_II) {
  int tempCycle = t_cycle;
  while (tempCycle < m_cycleBoundary) {
    if (canOccupy(t_dfgNode, tempCycle, t_II))
      return tempCycle;
    ++tempCycle;
  }
  return m_cycleBoundary;
}

int CGRANode::getCurrentCtrlMemItems() {
  return m_currentCtrlMemItems;
}

// TODO: will support precision-based operations (e.g., fadd, fmul, etc).
bool CGRANode::enableFunctionality(string t_func) {
  if (t_func.compare("store") == 0) {
    enableStore();
  } else if (t_func.compare("load") == 0) {
    enableLoad();
  } else if (t_func.compare("return") == 0) {
    enableReturn();
  } else if (t_func.find("call") != string::npos) {
    string type;
    const int kLengthOfCall = 4;
    if (t_func.length() == kLengthOfCall) {
      // The case corresponds to "call" : [...], i.e., no specific function name.
      type = "none";
    } else {
      // The case corresponds to "call-..." : [...], and the specific function name is provided.
      type = t_func.substr(t_func.find("call") + kLengthOfCall + 1);
    }
    enableCall(type);
  } else if (t_func.find("complex") != string::npos) {
    string type;
    const int kLengthOfComplex = 7;
    if (t_func.length() == kLengthOfComplex) {
      // The case corresponds to "complex" : [...], i.e., no specific pattern name.
      type = "none";
    } else {
      // The case corresponds to "complex-..." : [...], and the specific pattern name is provided.
      type = t_func.substr(t_func.find("complex") + kLengthOfComplex + 1);
    }
    enableComplex(type);
  } else if (t_func.compare("div") == 0) {
    enableDiv();
  }
  else {
    return false;
  }
  return true;
}

void CGRANode::enableReturn() {
  m_canReturn = true;
}

void CGRANode::enableStore() {
  m_canStore = true;
}

void CGRANode::enableLoad() {
  m_canLoad = true;
}

void CGRANode::enableCall(string t_func) {
  m_canCall.push_back(t_func);
}

void CGRANode::enableComplex(string type) {
  if (type == "") m_supportComplex = true;
  else m_supportComplexType.push_back(type);
}

void CGRANode::enableVectorization() {
  m_supportVectorization = true;
}

void CGRANode::enableAdd() {
  m_canAdd = true;
}

void CGRANode::enableMul() {
  m_canMul = true;
}

void CGRANode::enableShift() {
  m_canShift = true;
}

void CGRANode::enablePhi() {
  m_canPhi = true;
}

void CGRANode::enableSel() {
  m_canSel = true;
}

void CGRANode::enableCmp() {
  m_canCmp = true;
}

void CGRANode::enableMAC() {
  m_canMAC = true;
}

void CGRANode::enableLogic() {
  m_canLogic = true;
}

void CGRANode::enableBr() {
  m_canBr = true;
}

void CGRANode::enableDiv() {
  m_canDiv = true;
}

void CGRANode::disableMultipleOps() {
  printf("disabling multiple ops\n");
  m_canMultipleOps = false;
}

bool CGRANode::supportComplex(string type) {
  if (type == "") return m_supportComplex;
  for (string t: m_supportComplexType) {
    if (t.compare(type) == 0) return true;
  }
  return false;
}

bool CGRANode::supportVectorization() {
  return m_supportVectorization;
}

bool CGRANode::canCall(string t_func) {
  for (string func: m_canCall) {
    if (func.compare(t_func) == 0) {
      return true;
    }
  }
  return false;
}

bool CGRANode::canReturn() {
  return m_canReturn;
}

bool CGRANode::canStore() {
  return m_canStore;
}

bool CGRANode::canLoad() {
  return m_canLoad;
}

bool CGRANode::canAdd() {
  return m_canAdd;
}

bool CGRANode::canMul() {
  return m_canMul;
}

bool CGRANode::canShift() {
  return m_canShift;
}

bool CGRANode::canPhi() {
  return m_canPhi;
}

bool CGRANode::canSel() {
  return m_canSel;
}

bool CGRANode::canCmp() {
  return m_canCmp;
}

bool CGRANode::canMAC() {
  return m_canMAC;
}

bool CGRANode::canLogic() {
  return m_canLogic;
}

bool CGRANode::canBr() {
  return m_canBr;
}

bool CGRANode::canDiv() {
  return m_canDiv;
}

bool CGRANode::canMultipleOps() {
  return m_canMultipleOps;
}

int CGRANode::getX() {
  return m_x;
}

int CGRANode::getY() {
  return m_y;
}

void CGRANode::disable() {
  m_disabled = true;
  for (CGRALink* link: m_inLinks) {
    link->disable();
  }
  for (CGRALink* link: m_outLinks) {
    link->disable();
  }
}

void CGRANode::disableAllFUs() {
  m_canReturn = false;
  m_canStore = false;
  m_canLoad = false;
  m_canCall = vector<string>();
  m_supportComplexType = vector<string>();
  m_canAdd = false;
  m_canMul = false;
  m_canShift = false;
  m_canPhi = false;
  m_canSel = false;
  m_canCmp = false;
  m_canMAC = false;
  m_canLogic = false;
  m_canBr = false;
  m_supportComplex = false;
  m_supportVectorization = false;
}

bool CGRANode::isDisabled() {
    return m_disabled;
}
