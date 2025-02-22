/*
 * ======================================================================
 * DFGNode.cpp
 * ======================================================================
 * DFG node implementation.
 *
 * Author : Cheng Tan
 *   Date : Feb 12, 2020
 */

#include "DFGNode.h"
#include "llvm/Demangle/Demangle.h"

int testing_opcode_offset = 0;
string getOpcodeNameHelper(Instruction* inst);

DFGNode::DFGNode(int t_id, bool t_precisionAware, Instruction* t_inst,
                 StringRef t_stringRef, bool t_supportDVFS) {
  m_id = t_id;
  m_precisionAware = t_precisionAware;
  m_inst = t_inst;
  m_stringRef = t_stringRef;
  m_predNodes = NULL;
  m_succNodes = NULL;
  if (testing_opcode_offset == 0) {
    m_opcodeName = t_inst->getOpcodeName();
  } else {
    m_opcodeName = getOpcodeNameHelper(t_inst);
  }
  m_isMapped = false;
  m_numConst = 0;
  m_optType = "";
  m_combined = false;
  m_combinedtype = "";
  m_isPatternRoot = false;
  m_patternRoot = NULL;
  m_critical = false;
  m_cycleID = new list<int>();
  m_level = 0;
  m_execLatency = 1;
  m_pipelinable = false;
  m_isPredicatee = false;
  m_predicatees = NULL;
  m_isPredicater = false;
  m_patternNodes = new list<DFGNode*>();
  initType();
  m_supportDVFS = t_supportDVFS;
  m_DVFSLatencyMultiple = 1;
  // if (isMul()) {
  // if (!isPhi() and !isCmp() and !isScalarAdd() and !isBranch()) {
  //   m_DVFSLatencyMultiple = 2;
  // }
}

// used for the case of tuning division patterns
DFGNode::DFGNode(int t_id, DFGNode* old_node) {
  m_id = t_id;
  m_precisionAware = old_node->m_precisionAware;
  m_inst = old_node->m_inst;
  m_stringRef = old_node->m_stringRef;
  m_predNodes = old_node->m_predNodes;
  m_succNodes = old_node->m_succNodes;
  m_opcodeName = old_node->m_opcodeName;
  m_isMapped = old_node->m_isMapped;
  m_numConst = old_node->m_numConst;
  m_optType = old_node->m_optType;
  m_combined = old_node->m_combined;
  m_combinedtype = old_node->m_combinedtype;
  m_isPatternRoot = old_node->m_isPatternRoot;
  m_patternRoot = old_node->m_patternRoot;
  m_critical = old_node->m_critical;
  m_cycleID = old_node->m_cycleID;
  m_level = old_node->m_level;
  m_execLatency = old_node->m_execLatency;
  m_pipelinable = old_node->m_pipelinable;
  m_isPredicatee = old_node->m_isPredicatee;
  m_predicatees = old_node->m_predicatees;
  m_isPredicater = old_node->m_isPredicater;
  m_patternNodes = old_node->m_patternNodes;
  m_fuType = old_node->m_fuType;
}

int DFGNode::getID() {
  return m_id;
}

void DFGNode::setID(int t_id) {
  m_id = t_id;
}

void DFGNode::setLevel(int t_level) {
  m_level = t_level;
}

int DFGNode::getLevel() {
  return m_level;
}

void DFGNode::setCritical() {
  m_critical = true;
}

void DFGNode::addCycleID(int t_cycleID) {
  m_cycleID->push_back(t_cycleID);
}

list<int>* DFGNode::getCycleIDs() {
  return m_cycleID;
}

bool DFGNode::shareSameCycle(DFGNode* t_node) {
  list<int>* my_list = t_node->getCycleIDs();
  for (int cycleID: *m_cycleID) {
    bool found = (find(my_list->begin(), my_list->end(), cycleID) != my_list->end());
    if (found) {
      cout<<"[DEBUG] in shareSameCycle is true: node "<<t_node->getID()<<endl;
      return true;
    }
  }
  return false;
}

bool DFGNode::isCritical() {
  return m_critical;
}

void DFGNode::setPredicatee() {
  m_isPredicatee = true;
}

bool DFGNode::isPredicatee() {
  return m_isPredicatee;
}

bool DFGNode::isPredicater() {
  return m_isPredicater;
}

void DFGNode::addPredicatee(DFGNode* t_node) {
  m_isPredicater = true;
  if (m_predicatees == NULL) {
    m_predicatees = new list<DFGNode*>();
  }
  m_predicatees->push_back(t_node);
  t_node->setPredicatee();
}

list<DFGNode*>* DFGNode::getPredicatees() {
  return m_predicatees;
}

bool DFGNode::isMapped() {
  return m_isMapped;
}

void DFGNode::setMapped() {
  m_isMapped = true;
}

void DFGNode::clearMapped() {
  m_isMapped = false;
}

Instruction* DFGNode::getInst() {
  return m_inst;
}

StringRef DFGNode::getStringRef() {
  return m_stringRef;
}

string DFGNode::isCall() {
  string op = getOpcodeName();
  if (m_opcodeName.compare("call") != 0 || isVectorized() )
    return "None";
  return op;
}

bool DFGNode::isVectorized() {
  // TODO: need a more robust way to recognize vectorized instructions.
  Value* psVal = cast<Value>(m_inst);
  return psVal->getType()->isVectorTy();
}

bool DFGNode::isLoad() {
  if (m_opcodeName.compare("load") == 0)
    return true;
  return false;
}

bool DFGNode::isReturn() {
  if (m_opcodeName.compare("ret") == 0)
    return true;
  return false;
}

bool DFGNode::isStore() {
  if (m_opcodeName.compare("store") == 0)
    return true;
  return false;
}

bool DFGNode::isBranch() {
  if (m_opcodeName.compare("br") == 0)
    return true;
  return false;
}

bool DFGNode::isPhi() {
  if (m_opcodeName.compare("phi") == 0)
    return true;
  return false;
}

bool DFGNode::isOpt(string t_opt) {   
  if (m_opcodeName.compare(t_opt) == 0)
    return true;
  return false;
}

bool DFGNode::isMul() {
  if (m_opcodeName.compare("fmul") == 0 or
      m_opcodeName.compare("mul") == 0)
    return true;
  return false;
}

bool DFGNode::isAddSub() {
  if (m_opcodeName.compare("getelementptr") == 0 or
      m_opcodeName.compare("add") == 0  or
      m_opcodeName.compare("fadd") == 0 or
      m_opcodeName.compare("sub") == 0  or
      m_opcodeName.compare("fsub") == 0) {
    return true;
  }
  return false;
}

// Only detect integer addition.
bool DFGNode::isIaddIsub() {
  if (m_opcodeName.compare("getelementptr") == 0 or
      m_opcodeName.compare("add") == 0  or
      m_opcodeName.compare("sub") == 0) {
    return true;
  }
  return false;
}

// Checks whether the operation is a scalar addition.
bool DFGNode::isScalarAddSub() {
  if (m_opcodeName.compare("add") == 0 or
      m_opcodeName.compare("sub") == 0)
    return true;
  return false;
} 

bool DFGNode::isConstantAddSub() {
  if (auto* addInst = dyn_cast<BinaryOperator>(m_inst)) {
      if (addInst->getOpcode() == Instruction::Add) {
          Value* op1 = addInst->getOperand(0);
          Value* op2 = addInst->getOperand(1);
          return isa<ConstantInt>(op1) && isa<ConstantInt>(op2);
      }
  }
  return false;
}

bool DFGNode::isCmp() {
  if (m_opcodeName.compare("icmp") == 0 or m_opcodeName.compare("cmp") == 0)
    return true;
  return false;
}

bool DFGNode::isBitcast() {
  if (m_opcodeName.compare("bitcast") == 0)
    return true;
  return false;
}

bool DFGNode::isGetptr() {
  if (m_opcodeName.compare("getelementptr") == 0)
    return true;
  return false;
}

bool DFGNode::isSel() {
  if (m_opcodeName.compare("select") == 0)
    return true;
  return false;
}

bool DFGNode::isMAC() {
  if (m_opcodeName.compare("mulgetelementptr") == 0 or
      m_opcodeName.compare("muladd") == 0  or
      m_opcodeName.compare("mulfadd") == 0 or
      m_opcodeName.compare("mulsub") == 0  or
      m_opcodeName.compare("mulfsub") == 0  or
      m_opcodeName.compare("fmulgetelementptr") == 0 or
      m_opcodeName.compare("fmuladd") == 0  or
      m_opcodeName.compare("fmulfadd") == 0 or
      m_opcodeName.compare("fmulsub") == 0  or
      m_opcodeName.compare("fmulfsub") == 0)
    return true;
  return false;
}

bool DFGNode::isLogic() {
  if (m_opcodeName.compare("or") == 0 or m_opcodeName.compare("and") == 0)
    return true;
  return false;
}

// Divison can also be a special operation.
bool DFGNode::isDiv() {
  if (m_opcodeName.compare("fdiv") == 0 or m_opcodeName.compare("div") == 0)
    return true;
  return false;
}

// used for specialized fusion (e.g. alu+mul and icmp+br can be regared as two kinds of complex nodes, so there are different tiles to support them)
// type indicates the name of the combined node, which is specified by users. (e.g. ALU-MUL for alu+mul, CMP-BR for icmp+br)
// type = "" means the node is combined a special type, which is used for general fusion and compatibility with previous codes.
// general fusion: All complex nodes are in the same kind.
bool DFGNode::hasCombined() {
  return m_combined;
}

string DFGNode::getComplexType() {
  if (m_combined) return m_combinedtype;
  return "None";
}

void DFGNode::setCombine(string type) {
  m_combined = true;
  m_combinedtype = type;
}

void DFGNode::addPatternPartner(DFGNode* t_patternNode) {
  // setCombine() and setMerge() use the same addPatternPartner
  m_isPatternRoot = true;
  m_patternRoot = this;
  m_patternNodes->push_back(t_patternNode);
  t_patternNode->setPatternRoot(this);
  m_opcodeName += t_patternNode->getOpcodeName();
}

list<DFGNode*>* DFGNode::getPatternNodes() {
  return m_patternNodes;
}

void DFGNode::setPatternRoot(DFGNode* t_patternRoot) {
  m_patternRoot = t_patternRoot;
}

DFGNode* DFGNode::getPatternRoot() {
  return m_patternRoot;
}

bool DFGNode::isPatternRoot() {
  return m_isPatternRoot;
}

string DFGNode::getOpcodeName() {

  if (not m_precisionAware) {
    if (m_opcodeName.compare("fadd") == 0) {
      return "add";
    } else if (m_opcodeName.compare("fsub") == 0) {
      return "sub";
    } else if (m_opcodeName.compare("fmul") == 0) {
      return "mul";
    } else if (m_opcodeName.compare("fcmp") == 0) {
      return "cmp";
    } else if (m_opcodeName.compare("icmp") == 0) {
      return "cmp";
    } else if (m_opcodeName.compare("fdiv") == 0) {
      return "div";
    } else if (m_opcodeName.compare("call") == 0 && isVectorized()) {

      Function *func = ((CallInst*)m_inst)->getCalledFunction();
      if (func) {
        string newName = func->getName().str();
        string removingPattern = "llvm.vector.";
        int pos = newName.find(removingPattern);
        if (pos == -1)
        pos = newName.find("llvm.");
	      newName.erase(pos, removingPattern.length());
        string delimiter = ".v";
        newName = newName.substr(0, newName.find(delimiter));
	      replace(newName.begin(), newName.end(), '.', '_');
        return newName;
      }
      else
        return "indirect call";
    }
    // for the special operations
    else if (m_opcodeName.compare("call") == 0) {
      Function *func = ((CallInst*)m_inst)->getCalledFunction();
      if (func) {
        string newName = func->getName().str();
        newName = demangle(newName);
        return newName.substr(0, newName.find("("));
      }
      else return "indirect call";
    }
  }

  return m_opcodeName;
}

string DFGNode::getPathName(){
  return m_pathName;
}

string DFGNode::getFuType() {
  return m_fuType;
}

string DFGNode::getJSONOpt() {

  int numPred = 0;
  for (DFGEdge* edge: m_inEdges) {
    if (!edge->isCtrlEdge()) {
      numPred += 1;
    }
  }

  if (numPred < 2) {
    if (isPhi() or isCmp() or isGetptr() or m_opcodeName.compare("add") == 0 or
        m_opcodeName.compare("fadd") == 0 or m_opcodeName.compare("sub") == 0 or
        m_opcodeName.compare("fsub") == 0 or m_opcodeName.compare("fmul") == 0 or
        m_opcodeName.compare("mul") == 0 or m_opcodeName.compare("shl") == 0 or
        m_opcodeName.compare("lshr") == 0 or m_opcodeName.compare("ashr") == 0) {
      return m_optType + "_CONST";
    }
  }
  return m_optType;
}

void DFGNode::setDVFSLatencyMultiple(int t_DVFSLatencyMultiple) {
  // We allow 3 levels of DVFS, i.e., low, middle, and high. High level
  // is treated as the baseline, which has the latency as 1. The middle
  // level is 50% lower than the high level, which indicates 2 times
  // latency. The low level DVFS has the longest latency, which is 2
  // times of the middle level and 4 times of the high level.
  assert(t_DVFSLatencyMultiple == 1 || t_DVFSLatencyMultiple == 2 || t_DVFSLatencyMultiple == 4);
  m_DVFSLatencyMultiple = t_DVFSLatencyMultiple;
  setExecLatency(t_DVFSLatencyMultiple);
}

int DFGNode::getDVFSLatencyMultiple() {
  return m_DVFSLatencyMultiple;
}

void DFGNode::setExecLatency(int t_execLatency) {
  m_execLatency = t_execLatency;
}

int DFGNode::getExecLatency(int t_TileDVFSLatencyMultiple) {
  if (m_supportDVFS) {
    // assert(t_TileDVFSLatencyMultiple <= m_DVFSLatencyMultiple);
    return t_TileDVFSLatencyMultiple;
  }
  return m_execLatency;
}

bool DFGNode::isMultiCycleExec(int t_DVFSLatencyMultiple) {
  if (m_supportDVFS and t_DVFSLatencyMultiple > 1) {
    return true;
  }
  if (m_execLatency > 1) {
    return true;
  } else {
    return false;
  }
}

void DFGNode::setPipelinable() {
  m_pipelinable = true;
}

bool DFGNode::isPipelinable() {
  return m_pipelinable;
}

bool DFGNode::shareFU(DFGNode* t_dfgNode) {
  if (t_dfgNode->getFuType().compare(m_fuType) == 0) {
    return true;
  }
  return false;
}

void DFGNode::initType() {
  if (isLoad()) {
    m_optType = "OPT_LD";
    m_fuType = "MemUnit";
  } else if (isStore()) {
    m_optType = "OPT_STR";
    m_fuType = "MemUnit";
  } else if (isBranch()) {
    m_optType = "OPT_BRH";
    m_fuType = "Branch";
  } else if (isPhi()) {
    m_optType = "OPT_PHI";
    m_fuType = "Phi";
  } else if (isCmp()) {
    m_optType = "OPT_EQ";
    m_fuType = "Comp";
  } else if (isBitcast()) {
    m_optType = "OPT_NAH";
    m_fuType = "Alu";
  } else if (isGetptr()) {
    m_optType += "OPT_ADD";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("add") == 0) {
    m_optType = "OPT_ADD";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("sdiv") == 0) {
    m_optType = "OPT_DIV";
    m_fuType = "Div";
  } else if (m_opcodeName.compare("div") == 0) {
    m_optType = "OPT_DIV";
    m_fuType = "Div";
  } else if (m_opcodeName.compare("srem") == 0) {
    m_optType = "OPT_REM";
    m_fuType = "Div";
  } else if (m_opcodeName.compare("rem") == 0) {
    m_optType = "OPT_REM";
    m_fuType = "Div";
  } else if (m_opcodeName.compare("trunc") == 0) {
    m_optType = "OPT_TRUNC";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("select") == 0) {
    m_optType = "OPT_SEL";
    m_fuType = "Select";
  } else if (m_opcodeName.compare("ext") == 0) {
    m_optType = "OPT_EXT";
    m_fuType = "ext";
  } else if (m_opcodeName.compare("sext") == 0) {
    m_optType = "OPT_EXT";
    m_fuType = "sext";
  } else if (m_opcodeName.compare("zext") == 0) {
    m_optType = "OPT_EXT";
    m_fuType = "zext";
  } else if (m_opcodeName.compare("extractelement") == 0) {
    m_optType = "OPT_EXTRACT";
    m_fuType = "extract";
  } else if (m_opcodeName.compare("fadd") == 0) {
    m_optType = "OPT_ADD";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("sub") == 0) {
    m_optType = "OPT_SUB";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("fsub") == 0) {
    m_optType = "OPT_SUB";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("xor") == 0) {
    m_optType = "OPT_XOR";
    m_fuType = "Alu";
  } else if (m_opcodeName.compare("or") == 0) {
    m_optType = "OPT_OR";
    m_fuType = "Logic";
  } else if (m_opcodeName.compare("and") == 0) {
    m_optType = "OPT_AND";
    m_fuType = "Logic";
  } else if (m_opcodeName.compare("mul") == 0) {
    m_optType = "OPT_MUL";
    m_fuType = "Mul";
  } else if (m_opcodeName.compare("fmul") == 0) {
    m_optType = "OPT_MUL";
    m_fuType = "Mul";
  } else if (m_opcodeName.compare("shl") == 0) {
    m_optType = "OPT_SHL";
    m_fuType = "Shift";
  } else if (m_opcodeName.compare("lshr") == 0) {
    m_optType = "OPT_LSR";
    m_fuType = "Shift";
  } else if (m_opcodeName.compare("ashr") == 0) {
    m_optType = "OPT_ASR";
    m_fuType = "Shift";
  } // TODO: cooperate with RTL
  else if (getOpcodeName() == "lut") {
    m_optType = "OPT_LUT";
    m_fuType = "LUT";
  } else if (m_opcodeName.compare("fpQuantize") == 0) {
    m_optType = "OPT_Quantize";
    m_fuType = "Quantize";
  } else if (m_opcodeName.compare("intQuantize") == 0) {
    m_optType = "OPT_Quantize";
    m_fuType = "Quantize";
  } 
  else {
    m_optType = "Unfamiliar: " + m_opcodeName;
    m_fuType = "Unknown";
  }
}

list<DFGNode*>* DFGNode::getPredNodes() {
  if (m_predNodes != NULL) {
    return m_predNodes;
  }
    

  m_predNodes = new list<DFGNode*>();
  for (DFGEdge* edge: m_inEdges) {
    assert(edge->getDst() == this);
    m_predNodes->push_back(edge->getSrc());
  }
  if (isBranch()) {
    list<DFGNode*>* m_tempNodes = new list<DFGNode*>();
    for (DFGNode* node: *m_predNodes) {
      // make sure the CMP node is the last one in the predecessors,
      // so the JSON file will get the correct ordering.
      if (!node->isCmp()) {
        m_tempNodes->push_back(node);
      }
    }
    for (DFGNode* node: *m_predNodes) {
      if (node->isCmp()) {
        m_tempNodes->push_back(node);
      }
    }
    m_predNodes = m_tempNodes;
  }
  return m_predNodes;
}

list<DFGNode*>* DFGNode::getSuccNodes() {
  if (m_succNodes != NULL) {
  //   cout << "succ: ";
  // for (DFGNode* predNode: *m_succNodes) {
  //   cout << predNode->getID() << " ";
  // }
  // cout << endl;
    return m_succNodes;
  }
    

  m_succNodes = new list<DFGNode*>();
  for (DFGEdge* edge: m_outEdges) {
    assert(edge->getSrc() == this);
    m_succNodes->push_back(edge->getDst());
  }
  return m_succNodes;
}

void DFGNode::deleteSuccNode(DFGNode* node) {
  getSuccNodes()->remove(node);
}

void DFGNode::deletePredNode(DFGNode* node) {
  getPredNodes()->remove(node);
}

void DFGNode::setInEdge(DFGEdge* t_dfgEdge) {
  if (find(m_inEdges.begin(), m_inEdges.end(), t_dfgEdge) ==
      m_inEdges.end())
    m_inEdges.push_back(t_dfgEdge);
}

void DFGNode::setOutEdge(DFGEdge* t_dfgEdge) {
  if (find(m_outEdges.begin(), m_outEdges.end(), t_dfgEdge) ==
      m_outEdges.end())
    m_outEdges.push_back(t_dfgEdge);
}

void DFGNode::cutEdges() {
  m_inEdges.clear();
  m_outEdges.clear();

  if (m_predNodes != NULL) {
    m_predNodes = NULL;
  }
  if (m_succNodes != NULL) {
    m_succNodes = NULL;
  }
}

bool DFGNode::isSuccessorOf(DFGNode* t_dfgNode) {
  list<DFGNode*>* succNodes = t_dfgNode->getSuccNodes();
  if (find (succNodes->begin(), succNodes->end(), this) != succNodes->end())
    return true;
  return false;
}

bool DFGNode::isPredecessorOf(DFGNode* t_dfgNode) {
  list<DFGNode*>* predNodes = t_dfgNode->getPredNodes();
  if (find (predNodes->begin(), predNodes->end(), this) != predNodes->end())
    return true;
  return false;
}

bool DFGNode::isOneOfThem(list<DFGNode*>* t_pattern) {
  if (find (t_pattern->begin(), t_pattern->end(), this) != t_pattern->end())
    return true;
  return false;
}

void DFGNode::addConst() {
  ++m_numConst;
}

void DFGNode::removeConst() {
  --m_numConst;
}

int DFGNode::getNumConst() {
  return m_numConst;
}

string getOpcodeNameHelper(Instruction* inst) {

  unsigned opcode = inst->getOpcode();
  opcode -= testing_opcode_offset;
  if (opcode == Instruction::Mul) return "mul";
  if (opcode == Instruction::FMul) return "fmul";
  if (opcode == Instruction::Add) return "add";
  if (opcode == Instruction::FAdd) return "fadd";
  if (opcode == Instruction::Sub) return "sub";
  if (opcode == Instruction::FSub) return "fsub";
  if (opcode == Instruction::Xor) return "xor";
  if (opcode == Instruction::Or) return "or";
  if (opcode == Instruction::And) return "and";
  if (opcode == Instruction::SDiv) return "sdiv";
  if (opcode == Instruction::UDiv) return "udiv";
  if (opcode == Instruction::SRem) return "srem";
  if (opcode == Instruction::URem) return "urem";
  if (opcode == Instruction::Trunc) return "trunc";
  if (opcode == Instruction::ZExt) return "zext";
  if (opcode == Instruction::SExt) return "sext";
  if (opcode == Instruction::LShr) return "lshr";
  if (opcode == Instruction::AShr) return "ashr";
  if (opcode == Instruction::Load) return "load"; 
  if (opcode == Instruction::Store) return "store";
  if (opcode == Instruction::Br) return "br";
  if (opcode == Instruction::PHI) return "phi";
  if (opcode == Instruction::ICmp) return "icmp";
  if (opcode == Instruction::FCmp) return "fcmp";
  if (opcode == Instruction::BitCast) return "bitcast";
  if (opcode == Instruction::GetElementPtr) return "getelementptr";
  if (opcode == Instruction::Select) return "select";
  if (opcode == Instruction::ExtractElement) return "extractelement";
  if (opcode == Instruction::Call) return "call";
  
  return "unknown";
}
