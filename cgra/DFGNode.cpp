/*
 * ======================================================================
 * DFGNode.cpp
 * ======================================================================
 * DFG node implementation.
 *
 * Author : Cheng Tan
 *   Date : July 19, 2019
 */

#include "DFGNode.h"

DFGNode::DFGNode(int t_id, Instruction* t_inst, StringRef t_stringRef) {
  m_id = t_id;
  m_inst = t_inst;
  m_stringRef = t_stringRef;
  m_predNodes = NULL;
  m_succNodes = NULL;
  m_opcodeName = t_inst->getOpcodeName();
  m_isMapped = false;

}

int DFGNode::getID() {
  return m_id;
}

void DFGNode::setID(int t_id) {
  m_id = t_id;
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

bool DFGNode::isLoad() {
  if (m_opcodeName.compare("load") == 0)
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

bool DFGNode::isCmp() {
  if (m_opcodeName.compare("icmp") == 0)
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

string DFGNode::getOpcodeName() {
  return m_opcodeName;
}

string DFGNode::getJSONOpt() {
  if (isLoad())
    return "OPT_LD";
  else if (isStore())
    return "OPT_STR";
  else if (isBranch())
    return "OPT_BRH";
  else if (isPhi())
    return "OPT_PHI";
  else if (isCmp())
    return "OPT_CMP";
  else if (isBitcast())
    return "OPT_NAH";
  else if (isGetptr())
    return "OPT_ADD";
  else if (m_opcodeName.compare("add") == 0)
    return "OPT_ADD";
  else if (m_opcodeName.compare("fadd") == 0)
    return "OPT_ADD";
  else if (m_opcodeName.compare("sub") == 0)
    return "OPT_SUB";
  else if (m_opcodeName.compare("xor") == 0)
    return "OPT_XOR";
  else if (m_opcodeName.compare("or") == 0)
    return "OPT_OR";
  else if (m_opcodeName.compare("and") == 0)
    return "OPT_AND";
  else if (m_opcodeName.compare("mul") == 0)
    return "OPT_MUL";
  else if (m_opcodeName.compare("fmul") == 0)
    return "OPT_MUL";

  return "Unfamiliar: " + m_opcodeName;
}

list<DFGNode*>* DFGNode::getPredNodes() {
  if (m_predNodes != NULL)
    return m_predNodes;

  m_predNodes = new list<DFGNode*>();
  for (DFGEdge* edge: m_inEdges) {
    assert(edge->getDst() == this);
    m_predNodes->push_back(edge->getSrc());
  }
  return m_predNodes;
}

list<DFGNode*>* DFGNode::getSuccNodes() {
  if (m_succNodes != NULL)
    return m_succNodes;

  m_succNodes = new list<DFGNode*>();
  for (DFGEdge* edge: m_outEdges) {
    assert(edge->getSrc() == this);
    m_succNodes->push_back(edge->getDst());
  }
  return m_succNodes;
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

