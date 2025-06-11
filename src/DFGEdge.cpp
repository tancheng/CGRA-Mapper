/*
 * ======================================================================
 * DFGEdge.cpp
 * ======================================================================
 * DFG edge implementation.
 *
 * Author : Cheng Tan
 *   Date : July 19, 2019
 */

#include "DFGEdge.h"

DFGEdge::DFGEdge(int t_id, DFGNode* t_src, DFGNode* t_dst) {
  m_id = t_id;
  m_src = t_src;
  m_dst = t_dst;
  m_isCtrlEdge = false;
  m_isInterEdge = false;
}

DFGEdge::DFGEdge(int t_id, DFGNode* t_src, DFGNode* t_dst, bool t_isCtrlEdge) {
  m_id = t_id;
  m_src = t_src;
  m_dst = t_dst;
  m_isCtrlEdge = t_isCtrlEdge;
  m_isInterEdge = false;
  m_src->addPredicatee(m_dst);
}

void DFGEdge::setID(int t_id) {
  m_id = t_id;
}

int DFGEdge::getID() {
  return m_id;
}

DFGNode* DFGEdge::getSrc() {
  return m_src;
}

DFGNode* DFGEdge::getDst() {
  return m_dst;
}

void DFGEdge::connect(DFGNode* t_src, DFGNode* t_dst) {
  m_src = t_src;
  m_dst = t_dst;
}

DFGNode* DFGEdge::getConnectedNode(DFGNode* t_node) {
  if( t_node != m_src and t_node != m_dst)
    return NULL;
  if(m_src == t_node)
    return m_dst;
  else
    return m_src;
}

bool DFGEdge::isCtrlEdge() {
  return m_isCtrlEdge;
}

void DFGEdge::setInterEdge(bool t_isInterEdge) {
  if(m_isCtrlEdge) {
    cout<<"\033[0;31m"<<"[WARNING] Current DFGEdge is ctrl edge. Set m_isInterEdge = false."<<"\033[0m"<<endl;
    m_isInterEdge = false;
  }
  else {
    m_isInterEdge = t_isInterEdge;
  }
}

bool DFGEdge::isInterEdge() {
  return m_isInterEdge;
}