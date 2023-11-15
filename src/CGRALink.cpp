/*
 * ======================================================================
 * CGRALink.cpp
 * ======================================================================
 * CGRA link implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "CGRALink.h"
#include <assert.h>

CGRALink::CGRALink(int t_linkId) {
  setID(t_linkId);
  m_currentCtrlMemItems = 0;
  m_occupied = new bool[1];
  m_dfgNodes = new DFGNode*[1];
  m_bypassed = new bool[1];
  m_generatedOut = new bool[1];
  m_arrived = new bool[1];
  m_disabled = false;
  m_mapped = false;
}

void CGRALink::setCtrlMemConstraint(int t_ctrlMemConstraint) {
  m_ctrlMemSize = t_ctrlMemConstraint;
}

void CGRALink::setBypassConstraint(int t_bypassConstraint) {
  m_bypassConstraint = t_bypassConstraint;
}

void CGRALink::connect(CGRANode* t_src, CGRANode* t_dst) {
  m_src = t_src;
  m_dst = t_dst;
}

CGRANode* CGRALink::getConnectedNode(CGRANode* t_node) {
  if( t_node != m_src and t_node != m_dst)
    return NULL;
  if(m_src == t_node)
    return m_dst;
  else
    return m_src;
}

int CGRALink::getID() {
  return m_id;
}

void CGRALink::setID(int t_id) {
  m_id = t_id;
}

bool CGRALink::isMapped() {
  return m_mapped;
}

void CGRALink::constructMRRG(int t_CGRANodeCount, int t_II) {
  m_II = t_II;
  m_cycleBoundary = t_CGRANodeCount*t_II*t_II;
  delete[] m_occupied;
  m_occupied = new bool[m_cycleBoundary];
  delete[] m_dfgNodes;
  m_dfgNodes = new DFGNode*[m_cycleBoundary];
  delete[] m_bypassed;
  m_bypassed = new bool[m_cycleBoundary];
  delete[] m_generatedOut;
  m_generatedOut = new bool[m_cycleBoundary];
  delete[] m_arrived;
  m_arrived = new bool[m_cycleBoundary];
  m_currentCtrlMemItems = 0;
  for(int i=0; i<m_cycleBoundary; ++i) {
    m_occupied[i] = false;
    m_dfgNodes[i] = NULL;
    m_bypassed[i] = false;
    m_generatedOut[i] = false;
    m_arrived[i] = false;
  }
}

bool CGRALink::satisfyBypassConstraint(int t_cycle, int t_II) {
  CGRANode* outCGRANode = getDst();
  // If no DFG node is mapped onto the outCGRANode.
  if (!outCGRANode->isOccupied(t_cycle+1, t_II)) {
    int bypassCount = 0;
    list<CGRALink*>* incomingCGRALinks = outCGRANode->getInLinks();
    for (CGRALink* inLink: *incomingCGRALinks) {
      if (inLink == this) continue;
      if (inLink->isOccupied(t_cycle) and inLink->isBypass(t_cycle)) {
        ++bypassCount;
      }
    }
    if (bypassCount >= m_bypassConstraint) {
      return false;
    }
  } else {
    int bypassCount = 1;
    list<CGRALink*>* incomingCGRALinks = outCGRANode->getInLinks();
    for (CGRALink* inLink: *incomingCGRALinks) {
      if (inLink == this) continue;
      if (inLink->isOccupied(t_cycle) and inLink->isBypass(t_cycle)) {
        ++bypassCount;
      }
    }
    if (bypassCount >= m_bypassConstraint) {
      return false;
    }
  }
  return true;
}

// The occupancy is special for the ue-cgra, whose current design
// can only support one bypass and one computation. So at most two bypass.
bool CGRALink::canOccupy(int t_cycle, int t_II) {
  // cout<<"[link->canOccupy() 0] ("<<m_src->getID()<<")->("<<m_dst->getID()<<")..."<<endl;
  if (m_disabled)
    return false;
  if (m_currentCtrlMemItems + 1 > m_ctrlMemSize)
    return false;
  if (m_occupied[t_cycle])
    return false;
  if (!satisfyBypassConstraint(t_cycle, t_II))
    return false;
  return true;
}

bool CGRALink::canOccupy(DFGNode* t_srcDFGNode, CGRANode* t_srcCGRANode,
                         int t_cycle, int t_II) {

  // cout<<"[link->canOccupy() 1] ("<<m_src->getID()<<")->("<<m_dst->getID()<<")..."<<endl;
  if (m_disabled)
    return false;
  if (m_dfgNodes[t_cycle] != NULL and t_srcDFGNode == m_dfgNodes[t_cycle])
    return true;
  if (m_currentCtrlMemItems + 1 > m_ctrlMemSize)
    return false;
  if (m_occupied[t_cycle])
    return false;
  if (!satisfyBypassConstraint(t_cycle, t_II))
    return false;

  // The current design of the lightweight xbar has some constrains.
  // The case of resultOut that is blocked by the bypass (blocking
  // the port/register) for 2 cycles:
  if (getSrc() == t_srcCGRANode) {
    int t = (t_cycle+1) % t_II;
    if (m_dfgNodes[t] != NULL and
        !m_generatedOut[t]) {
      return false;
    }
  } else { // On the other hand, the link for bypass is blocked
           // by the resultOut for 2 cycles:
    int t = (t_cycle+t_II-1) % t_II;
    if (m_dfgNodes[t] != NULL and
        m_generatedOut[t]) {
      return false;
    }
  }

  // Checks whether the DVFS long execution (low frequency indicates
  // `pseudo` multi-cycle execution) is enabled. If enabled, only the
  // last cycle (i.e., last pipe stage) can send out the data. This
  // feature is used to mimic the asynchronous buffer on the link.
  // if (getSrc()->isFrequencyLowered() && !getSrc()->isEndPipe(t_cycle, t_II)) {
  // FIXME: this should be revised to align with the sync().
  int cycle_in_II = (t_cycle+t_II) % t_II;
  if (getDst()->isDVFSEnabled() and getDst()->getDVFSLatencyMultiple() > 1 and
      cycle_in_II % getDst()->getDVFSLatencyMultiple() != 0) {
  // if (getDst()->isDVFSEnabled() and getDst()->getDVFSLatencyMultiple() > 1 and
  //     cycle_in_II % getDst()->getDVFSLatencyMultiple() == 1) {
  //   // The output should be blocked by the low frequency computation.
  //   // This should roughly model the behavior of the DVFS asynchronous
  //   // buffer.
    return false;
  }

  return true;
}

/*
bool CGRALink::canOccupy(int t_cycle, int t_II) {
  if (m_currentCtrlMemItems + 1 > m_ctrlMemSize)
    return false;
  return !m_occupied[t_cycle];
}

bool CGRALink::canOccupy(DFGNode* t_srcDFGNode, int t_cycle, int t_II) {
  if (m_dfgNodes[t_cycle] != NULL and t_srcDFGNode == m_dfgNodes[t_cycle])
    return true;
  if (m_currentCtrlMemItems + 1 > m_ctrlMemSize)
    return false;
  return !m_occupied[t_cycle];
}
*/

bool CGRALink::isOccupied(int t_cycle) {
  return m_occupied[t_cycle];
}

bool CGRALink::isOccupied(int t_cycle, int t_II, bool t_isStaticElasticCGRA) {
  int interval = t_II;
  if (t_isStaticElasticCGRA)
    interval = 1;
  for (int i=t_cycle; i<m_cycleBoundary; i=i+interval) {
    if (m_occupied[i]) {
      return true;
    }
  }
  return false;
}

bool CGRALink::isReused(int t_cycle) {
  return m_occupied[t_cycle];
}

void CGRALink::occupy(DFGNode* t_srcDFGNode, int t_cycle, int duration,
    int t_II, bool t_isBypass, bool t_isGeneratedOut, bool t_isStaticElasticCGRA) {
  m_mapped = true;
  int interval = t_II;
  if (t_isStaticElasticCGRA) {
    interval = 1;
    t_cycle = 0;
  }
  for(int cycle=t_cycle; cycle<m_cycleBoundary; cycle+=interval) {
    m_dfgNodes[cycle] = t_srcDFGNode;
    m_occupied[cycle] = true;
    // Only set 'm_bypassed' as true if it is bypassed.
    // Will never set it back to false.
    if (t_isBypass)
      m_bypassed[cycle] = true;
    if (t_isGeneratedOut)
      m_generatedOut[cycle] = true;
    // Only set 'm_arrived' as true if it is not bypassed.
    // Will never set it back to false.
    if (!t_isBypass)
      m_arrived[cycle] = true;
  }
  for(int cycle=t_cycle; cycle>=0; cycle-=interval) {
    m_dfgNodes[cycle] = t_srcDFGNode;
    m_occupied[cycle] = true;
    // Only set 'm_bypassed' as true if it is bypassed.
    // Will never set it back to false.
    if (t_isBypass)
      m_bypassed[cycle] = true;
    if (t_isGeneratedOut)
      m_generatedOut[cycle] = true;
    // Only set 'm_arrived' as true if it is not bypassed.
    // Will never set it back to false.
    if (!t_isBypass)
      m_arrived[cycle] = true;
  }
  if (!t_isBypass) {
    m_dst->allocateReg(this, t_cycle, duration, interval);
  }

  ++m_currentCtrlMemItems;

  cout<<"[DEBUG] occupy link["<<m_src->getID()<<"]-->["<<m_dst->getID()<<"] (bypass:"<<t_isBypass<<") dfgNode: "<<t_srcDFGNode->getID()<<" at cycle "<<t_cycle<<"\n";
}

DFGNode* CGRALink::getMappedDFGNode(int t_cycle) {
  if (t_cycle < 0) {
    return m_dfgNodes[m_II+t_cycle];
  }
  return m_dfgNodes[t_cycle];
}

bool CGRALink::isBypass(int t_cycle) {
  return m_bypassed[t_cycle];
}

CGRANode* CGRALink::getSrc() {
  return m_src;
}
CGRANode* CGRALink::getDst() {
  return m_dst;
}

int CGRALink::getDirectionID(CGRANode* t_cgraNode) {
  if (m_src == t_cgraNode) {
    if (m_src->getX() > m_dst->getX())
      // return "W";
      return 2;
    else if (m_src->getX() < m_dst->getX())
      // return "E";
      return 3;
    else if (m_src->getY() > m_dst->getY())
      // return "S";
      return 1;
    else if (m_src->getY() < m_dst->getY())
      // return "N";
      return 0;
  } else {
    assert(m_dst == t_cgraNode);
    if (m_src->getX() > m_dst->getX())
      // return "E";
      return 3;
    else if (m_src->getX() < m_dst->getX())
      // return "W";
      return 2;
    else if (m_src->getY() > m_dst->getY())
      // return "N";
      return 0;
    else if (m_src->getY() < m_dst->getY())
      // return "S";
      return 1;
  }
  return -1;
}

string CGRALink::getDirection(CGRANode* t_cgraNode) {
  if (m_src == t_cgraNode) {
    if (m_src->getX() > m_dst->getX())
      return "W";
    else if (m_src->getX() < m_dst->getX())
      return "E";
    else if (m_src->getY() > m_dst->getY())
      return "S";
    else if (m_src->getY() < m_dst->getY())
      return "N";
  } else {
    assert(m_dst == t_cgraNode);
    if (m_src->getX() > m_dst->getX())
      return "E";
    else if (m_src->getX() < m_dst->getX())
      return "W";
    else if (m_src->getY() > m_dst->getY())
      return "N";
    else if (m_src->getY() < m_dst->getY())
      return "S";
  }
  return "self";
}

void CGRALink::disable() {
  m_disabled = true;
}
