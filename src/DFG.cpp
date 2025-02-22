/*
 * ======================================================================
 * DFG.cpp
 * ======================================================================
 * DFG implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include <fstream>
#include "DFG.h"

DFG::DFG(Function& t_F, list<Loop*>* t_loops, bool t_targetFunction,
         bool t_precisionAware, bool t_heterogeneity,
         map<string, int>* t_execLatency, list<string>* t_pipelinedOpt,
         map<string, list<string>*>* t_fusionPattern, 
	      bool t_supportDVFS, bool t_DVFSAwareMapping,
	      int t_vectorFactorForIdiv) {
  m_num = 0;
  m_targetFunction = t_targetFunction;
  m_targetLoops = t_loops;
  m_orderedNodes = NULL;
  m_CDFGFused = false;
  m_cycleNodeLists = new list<list<DFGNode*>*>();
  m_precisionAware = t_precisionAware;
  m_supportDVFS = t_supportDVFS;
  m_DVFSAwareMapping = t_DVFSAwareMapping;
  m_vectorFactorForIdiv = t_vectorFactorForIdiv;

  construct(t_F);
//  tuneForBranch();
//  tuneForLoad();
  if (t_heterogeneity) {
    nonlinear_combine();      // fusion for nonlinear ops
    // ctrlFlow_combine(t_fusionPattern); // fusion for control flows
    calculateCycles();
//    tuneForPattern();
  }
//  trimForStandalone();
  initExecLatency(t_execLatency);
  initPipelinedOpt(t_pipelinedOpt);

  // Pre-assigns the DVFS levels to each DFG node.
  // This needs to be done after construct function
  // as we need assign the highest frequency to the
  // nodes on the critical path in the DFG.
}

void DFG::initDVFSLatencyMultiple(int t_II, int t_DVFSIslandDim,
		                  int t_numTiles) {
  list<list<DFGNode*>*>* cycles = getCycleLists();
  float max_cycle_length = 1.0;
  for (list<DFGNode*>* cycle: *cycles) {
    if (cycle->size() > max_cycle_length) {
      max_cycle_length = cycle->size();
    }
  }
  set<DFGNode*> assigned_dvfs_nodes;
  int high_dvfs_dfg_nodes = 0;
  int mid_dvfs_dfg_nodes = 0;
  int low_dvfs_dfg_nodes = 0;
  // TODO: might need to assign DVFS level based on the
  // number of available CGRA nodes/resources.
  for (list<DFGNode*>* cycle: *cycles) {
    if (cycle->size() > max_cycle_length / 2) {
      for (auto dfg_node : *cycle) {
        dfg_node->setDVFSLatencyMultiple(1);
	assigned_dvfs_nodes.insert(dfg_node);
	high_dvfs_dfg_nodes += 1;
      }
    } else {
      for (auto dfg_node : *cycle) {
	if (assigned_dvfs_nodes.count(dfg_node) == 0) {
          dfg_node->setDVFSLatencyMultiple(2);
	  assigned_dvfs_nodes.insert(dfg_node);
	  mid_dvfs_dfg_nodes += 1;
	}
      }
    }
  }

  int num_tiles_in_island = t_DVFSIslandDim * t_DVFSIslandDim;
  int unused_high_dvfs_cgra_tiles_across_II =
        t_II * num_tiles_in_island *
	((high_dvfs_dfg_nodes + num_tiles_in_island - 1) / num_tiles_in_island) -
        high_dvfs_dfg_nodes;
  int unused_mid_dvfs_cgra_tiles_across_II =
        (t_II * num_tiles_in_island *
	 ((mid_dvfs_dfg_nodes + num_tiles_in_island - 1) / num_tiles_in_island) -
         mid_dvfs_dfg_nodes * 2) / 2;
  int unused_low_dvfs_cgra_tiles_across_II =
        (t_II * t_numTiles -
          (t_II * num_tiles_in_island *
            ((high_dvfs_dfg_nodes + num_tiles_in_island - 1) / num_tiles_in_island)) -
	  (t_II * num_tiles_in_island *
            ((mid_dvfs_dfg_nodes + num_tiles_in_island - 1) / num_tiles_in_island))
        ) / 4;
  cout << "[debug] unused_high_dvfs_cgra_tiles_across_II: " << unused_high_dvfs_cgra_tiles_across_II << endl;
  cout << "[debug] unused_mid_dvfs_cgra_tiles_across_II: " << unused_mid_dvfs_cgra_tiles_across_II << endl;
  cout << "[debug] unused_low_dvfs_cgra_tiles_across_II: " << unused_low_dvfs_cgra_tiles_across_II << endl;

  int unlabeled_dfg_nodes = 0;
  for (auto node : nodes) {
    if (assigned_dvfs_nodes.count(node) == 0) {
      unlabeled_dfg_nodes += 1;
    }
  }
  if (unlabeled_dfg_nodes > unused_low_dvfs_cgra_tiles_across_II) {
    int min_reserved_low_dvfs_tiles_across_II = unused_low_dvfs_cgra_tiles_across_II / 4.5;
    int num_low_dvfs_dfg_nodes = 0;
    for (auto node : nodes) {
      if (assigned_dvfs_nodes.count(node) == 0) {
        node->setDVFSLatencyMultiple(4);
        assigned_dvfs_nodes.insert(node);
        num_low_dvfs_dfg_nodes += 1;
        if (num_low_dvfs_dfg_nodes >= min_reserved_low_dvfs_tiles_across_II) {
          unused_low_dvfs_cgra_tiles_across_II -= num_low_dvfs_dfg_nodes;
          break;
        }
      }
    }
  } else {
    for (auto node : nodes) {
      if (assigned_dvfs_nodes.count(node) == 0) {
        node->setDVFSLatencyMultiple(4);
        assigned_dvfs_nodes.insert(node);
      }
    }
    unused_low_dvfs_cgra_tiles_across_II -= unlabeled_dfg_nodes;
  }

  for (auto node : nodes) {
    if (assigned_dvfs_nodes.count(node) == 0) {
      if (unused_high_dvfs_cgra_tiles_across_II > 0) {
        // High DVFS islands have the highest priority as we don't want to
	// waste it.
        node->setDVFSLatencyMultiple(1);
        assigned_dvfs_nodes.insert(node);
        unused_high_dvfs_cgra_tiles_across_II -= 1;
	unused_mid_dvfs_cgra_tiles_across_II -= 1;
	unused_low_dvfs_cgra_tiles_across_II -= 1;
      } else if (unused_mid_dvfs_cgra_tiles_across_II > 0) {
        // Then try to allocate the DFG node into the mid DVFS island if the
	// high DVFS islands are used up.
        node->setDVFSLatencyMultiple(2);
        assigned_dvfs_nodes.insert(node);
        unused_high_dvfs_cgra_tiles_across_II -= 2;
        unused_mid_dvfs_cgra_tiles_across_II -= 1;
        unused_low_dvfs_cgra_tiles_across_II -= 1;
      } else if (unused_low_dvfs_cgra_tiles_across_II > 0) {
        // Low DVFS islands have the lowest priority.
        node->setDVFSLatencyMultiple(4);
        assigned_dvfs_nodes.insert(node);
        unused_high_dvfs_cgra_tiles_across_II -= 4;
        unused_mid_dvfs_cgra_tiles_across_II -= 2;
        unused_low_dvfs_cgra_tiles_across_II -= 1;
      } else {
	// If all the islands assuming the optimal II are used up, label
	// the left DFG nodes with highest DVFS level as we don't want
	// to dramatically increase the II unnecessarily, which would
	// lead to bad performance.
        node->setDVFSLatencyMultiple(1);
        assigned_dvfs_nodes.insert(node);
      }
    }
  }
}

// Specilized fusion for the nonlinear operations.
void DFG::nonlinear_combine() {
  tuneForBitcast();
  combineMulAdd("CoT");
  combinePhiAdd("BrT");
  combine("fcmp", "select", "BrT");
  combine("icmp", "select", "BrT");
  combine("icmp", "br", "CoT");
  combine("fcmp", "br", "CoT");
  combineAddAdd("BrT");
  tuneForPattern();
  tuneDivPattern();
}

// For division, we treat it as non-vectorized instructions, which is contradictory to LLVM Pass.
// Thus we need to split a vectorization divison into multiple scalar divisions.
void DFG::tuneDivPattern() {
  list<DFGNode*>* removeNodes = new list<DFGNode*>();
  list<DFGNode*>* splitNodes = new list<DFGNode*>();
  int dfgNodeID = nodes.size();
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isOpt("sdiv") && dfgNode->isVectorized()) {
      DFGNode* newNodes[m_vectorFactorForIdiv];
      newNodes[0] = new DFGNode(dfgNode->getID(), dfgNode);
      for (int i = 1; i < m_vectorFactorForIdiv; i++) {
        newNodes[i] = new DFGNode(dfgNodeID++, dfgNode);
      }
      for (DFGNode* predNode: *(dfgNode->getPredNodes())) {
        if (!(predNode == dfgNode or
            predNode->isOneOfThem(dfgNode->getPatternNodes()))) {
          if (predNode->hasCombined())
            predNode = predNode->getPatternRoot();
          DFGNode* predNodes[m_vectorFactorForIdiv];
          for (int i = 0; i < m_vectorFactorForIdiv; i++) {
            predNodes[i] = predNode;
          }
          replaceMultipleDFGEdge(predNode, dfgNode, predNodes, newNodes);
          predNode->deleteSuccNode(dfgNode);
          continue;
        }
      }
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (!(succNode == dfgNode or
            succNode->isOneOfThem(dfgNode->getPatternNodes()))) {
          if (succNode->hasCombined())
            succNode = succNode->getPatternRoot();
          DFGNode* succNodes[m_vectorFactorForIdiv];
          for (int i = 0; i < m_vectorFactorForIdiv; i++) {
            succNodes[i] = succNode;
          }
          replaceMultipleDFGEdge(dfgNode, succNode, newNodes, succNodes);
          succNode->deletePredNode(dfgNode);
          continue;
        }
      }
      for (int i = 0; i < m_vectorFactorForIdiv; i++) splitNodes->push_back(newNodes[i]);
      removeNodes->push_back(dfgNode);
    }
  }
  for (DFGNode* dfgNode: *removeNodes) {
    nodes.remove(dfgNode);
  }
  for (DFGNode *dfgNode: *splitNodes) {
    nodes.push_back(dfgNode);
  }
}

// Fusion for control flows using t_fusionPattern.
void DFG::ctrlFlow_combine(map<string, list<string>*>* t_fusionPattern) {
  for (map<string, list<string>*>::iterator iter=t_fusionPattern->begin();
          iter!=t_fusionPattern->end(); ++iter) {
          combineForIter(iter->second, "BrT");
        }
  // combineForUnroll only resloves "phi-ConstantAdd-ConstantAdd-..." 
  combineForUnroll();
  tuneForPattern();
}

// FIXME: only combine operations of mul+alu and alu+cmp for now,
//        since these two are the most common patterns across all
//        the kernels.
void DFG::tuneForPattern() {
  // reconstruct connected DFG by modifying m_DFGEdge
  list<DFGNode*>* removeNodes = new list<DFGNode*>();
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->hasCombined()) {
      if (dfgNode->isPatternRoot()) {
        for (DFGNode* patternNode: *(dfgNode->getPatternNodes())) {
          if (hasDFGEdge(dfgNode, patternNode))
            m_DFGEdges.remove(getDFGEdge(dfgNode, patternNode));
          for (DFGNode* predNode: *(patternNode->getPredNodes())) {
            if (predNode == dfgNode or
                predNode->isOneOfThem(dfgNode->getPatternNodes())) {
              deleteDFGEdge(predNode, patternNode);
              continue;
            }
            DFGNode* newPredNode = NULL;
            if (predNode->hasCombined())
              newPredNode = predNode->getPatternRoot();
            else
              newPredNode = predNode;
            replaceDFGEdge(predNode, patternNode, newPredNode, dfgNode);
          }
          for (DFGNode* succNode: *(patternNode->getSuccNodes())) {
            if (succNode == dfgNode or
                succNode->isOneOfThem(dfgNode->getPatternNodes())) {
              deleteDFGEdge(patternNode, succNode);
              continue;
            }
            DFGNode* newSuccNode = NULL;
            if (succNode->hasCombined())
              newSuccNode = succNode->getPatternRoot();
            else
              newSuccNode = succNode;
            replaceDFGEdge(patternNode, succNode, dfgNode, newSuccNode);
          }

        }
      } else {
        removeNodes->push_back(dfgNode);
      }
    }
  }
  for (DFGNode* dfgNode: *removeNodes) {
    nodes.remove(dfgNode);
  }
}

void DFG::combineCmpBranch() {
  // detect patterns (e.g., cmp+branch)
  DFGNode* addNode = NULL;
  DFGNode* cmpNode = NULL;
  DFGNode* brhNode = NULL;
  bool found = false;
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isAddSub() and !dfgNode->hasCombined()) {
      found = false;
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (succNode->isCmp() and !succNode->hasCombined()) {
          for (DFGNode* succSuccNode: *(succNode->getSuccNodes())) {
            if (succSuccNode->isBranch() and !succSuccNode->hasCombined() and
                succSuccNode->isSuccessorOf(dfgNode)) {
              addNode = dfgNode;
              addNode->setCombine();
              cmpNode = succNode;
              addNode->addPatternPartner(cmpNode);
              cmpNode->setCombine();
              brhNode = succSuccNode;
              addNode->addPatternPartner(brhNode);
              brhNode->setCombine();
              found = true;
              break;
            }
          }
        }
        if (found) break;
      }
    }
  }
}

// Combine phi + iadd or phi + iadd + iadd where iadd is integer addition.
void DFG::combinePhiAdd(string type) {
  // detect patterns (e.g., mul+alu)
  DFGNode* phiNode = NULL;
  DFGNode* addNode = NULL;
  DFGNode* addNode2 = NULL;
  bool found = false;
  // TODO: When a phi has multiple iadd, it would simply pick the first one no matter 
  // whether the second one has grandchild iadd, i.e., we may unfortunately skip the 
  // best opportunities of maximum fusion. 
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isPhi() and !dfgNode->hasCombined()) {
      found = false;
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (found) break;
        if (succNode->isIaddIsub() and !succNode->hasCombined()) {
          for (DFGNode* succNode2: *(succNode->getSuccNodes())) {
            if (succNode2->isIaddIsub() and !succNode2->hasCombined()) {
              phiNode = dfgNode;
              phiNode->setCombine(type);
              addNode = succNode;
              phiNode->addPatternPartner(addNode);
              addNode->setCombine(type);
              addNode2 = succNode2;
              phiNode->addPatternPartner(addNode2);
              addNode2->setCombine(type);
              found = true;
              break;
            }
          }
        }
      }
    }
  }
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isPhi() and !dfgNode->hasCombined()) {
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (succNode->isIaddIsub() and !succNode->hasCombined()) {
          phiNode = dfgNode;
          phiNode->setCombine(type);
          addNode = succNode;
          phiNode->addPatternPartner(addNode);
          addNode->setCombine(type);
          break;
        }
      }
    }
  }
}

// Combine add & mul followed by add. The mul + add will also be combined.
void DFG::combineMulAdd(string type) {
  // detect patterns (e.g., mul+alu)
  DFGNode* mulNode = NULL;
  DFGNode* addNode = NULL;
  DFGNode* addNode2 = NULL;
  bool found = false;
  // We first locate the latter addition node, then try to find its predecessor multiplication node and another addition node.
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isAddSub() and !dfgNode->hasCombined()) {
      found = false;
      for (DFGNode* predNode: *(dfgNode->getPredNodes())) {
        if (found) break;
        if (predNode->isMul() and !predNode->hasCombined()) {
          for (DFGNode* predNode2: *(dfgNode->getPredNodes())) {
            if (predNode2->isAddSub() and !predNode2->hasCombined()) {
              mulNode = dfgNode;
              mulNode->setCombine(type);
              addNode = predNode;
              mulNode->addPatternPartner(addNode);
              addNode->setCombine(type);
              addNode2 = predNode2;
              mulNode->addPatternPartner(addNode2);
              addNode2->setCombine(type);
              found = true;
              break;
            }
          }
        }
      }
    }
  }
  // This loop is to fuse mul + add.
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isMul() and !dfgNode->hasCombined()) {
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (succNode->isAddSub() and !succNode->hasCombined()) {
          mulNode = dfgNode;
          mulNode->setCombine(type);
          addNode = succNode;
          mulNode->addPatternPartner(addNode);
          addNode->setCombine(type);
          break;
        }
      }
    }
  }
}

// Combine add + add. 
void DFG::combineAddAdd(string type) {
  DFGNode* mulNode = NULL;
  DFGNode* addNode = NULL;
  DFGNode* addNode2 = NULL;
  bool found = false;
  
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isAddSub() and !dfgNode->hasCombined()) {
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (succNode->isAddSub() and !succNode->hasCombined()) {
          mulNode = dfgNode;
          mulNode->setCombine(type);
          addNode = succNode;
          mulNode->addPatternPartner(addNode);
          addNode->setCombine(type);
          break;
        }
      }
    }
  }
}

void DFG::combine(string t_opt0, string t_opt1, string type) {
  DFGNode* opt0Node = NULL;
  DFGNode* opt1Node = NULL;
  bool found = false;
  for (DFGNode* dfgNode: nodes) {
//    if (dfgNode->isOpt(t_opt0) and dfgNode->isCritical() and !dfgNode->hasCombined()) {
    if (dfgNode->isOpt(t_opt0) and !dfgNode->hasCombined()) {
      for (DFGNode* succNode: *(dfgNode->getSuccNodes())) {
        if (succNode->isOpt(t_opt1) and !succNode->hasCombined()) {
          opt0Node = dfgNode;
          opt0Node->setCombine(type);
          opt1Node = succNode;
          opt0Node->addPatternPartner(opt1Node);
          opt1Node->setCombine(type);
          break;
        }
      }
    }
  }
}

// Combines patterns provided by users which should be a cycle, otherwise, the fusion won't be performed.
void DFG::combineForIter(list<string>* t_targetPattern, string type) {  
  int patternSize = t_targetPattern->size();
  string headOpt = string(t_targetPattern->front());
  list<string>::iterator currentFunc = t_targetPattern->begin();
  currentFunc++;
  // toBeMatchedDFGNodes is to store the DFG nodes that match the pattern
  list<DFGNode*>* toBeMatchedDFGNodes = new list<DFGNode*>[patternSize];
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isOpt(headOpt) and !dfgNode->hasCombined()) {
      toBeMatchedDFGNodes->push_back(dfgNode);
      cout << "[MMJ] toBeMatchedDFGNodes is " << dfgNode->getID() << endl;
      // the for loop below is to find the target pattern under specific dfgNode
      for (int i = 1; i < patternSize; i++, currentFunc++){
        string t_opt = *currentFunc;
        DFGNode* tailNode = toBeMatchedDFGNodes->back();
        for (DFGNode* succNode: *(tailNode->getSuccNodes())) {
          if (succNode->isOpt(t_opt) and !succNode->hasCombined()) {
            // Indicate the pattern is finally found and matched
            if (i == (patternSize-1) and dfgNode->isSuccessorOf(succNode)){
              toBeMatchedDFGNodes->push_back(succNode);
              for(DFGNode* optNode: *toBeMatchedDFGNodes){
                if(optNode != dfgNode){
                   dfgNode ->addPatternPartner(optNode);                  
                }
                optNode->setCombine();                   
              }
              break;
            } else if(i == (patternSize-1) and !dfgNode->isSuccessorOf(succNode)){
              continue;
            } else{
              toBeMatchedDFGNodes->push_back(succNode);
              break;
            }
          }
        }        
      }
      toBeMatchedDFGNodes->clear();
      currentFunc = t_targetPattern->begin();
      currentFunc++;
    }  
  }
}

// combineForUnroll is used to reconstruct "phi-ConstantAdd-ConstantAdd-..." alike circles with a limited length 4.
void DFG::combineForUnroll(string type) {
  bool combineDone = false;
  bool foundNext = false;
  int limitedSize = 4;
  list<DFGNode*> currentPath;
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isPhi() and !dfgNode->hasCombined()) {
      currentPath.push_back(dfgNode);
      // the for loop below is to find ConstantAdd under specific phi dfgNode
      for (int i = 1; i < limitedSize; i++) {
        DFGNode* tailNode = currentPath.back();
        for (DFGNode* succNode: *(tailNode->getSuccNodes())) {
          if (succNode->isConstantAddSub() and !succNode->hasCombined()) {
            currentPath.push_back(succNode);
            foundNext = true;
            if (dfgNode->isSuccessorOf(succNode)) { 
              // must be a circle
              for(DFGNode* optNode: currentPath){
                if(optNode != dfgNode){
                   dfgNode ->addPatternPartner(optNode);                  
                }
                optNode->setCombine();                       
              }
              combineDone = true;   
            }
            break;
          }
        }
        // if can't find any avaible succNode, then break
        if (!foundNext) break;
        // if combine is done, then break
        if (combineDone) break;
      }
      currentPath.clear();
      combineDone = false;
      foundNext = false;
    }
  }
}

bool DFG::shouldIgnore(Instruction* t_inst) {
  if (m_targetFunction) {
    return false;
  }
  if (m_targetLoops->size() == 0)
    return false;
  for (Loop* current_loop: *m_targetLoops) {
    if (current_loop->contains(t_inst)) {
      return false;
    }
  }
  return true;
}

list<DFGNode*>* DFG::getDFSOrderedNodes() {
  if (m_orderedNodes != NULL)
    return m_orderedNodes;
  m_orderedNodes = new list<DFGNode*>();
  list<DFGNode*> tempNodes;
  while (m_orderedNodes->size() < nodes.size()) {
    DFGNode* startNode = NULL;
    int curWithMaxSucc = 0;
    for (DFGNode* dfgNode: nodes) {
      if (find(m_orderedNodes->begin(), m_orderedNodes->end(), dfgNode) ==
          m_orderedNodes->end()) {
        if (dfgNode->getSuccNodes()->size() > curWithMaxSucc) {
          curWithMaxSucc = dfgNode->getSuccNodes()->size();
          startNode = dfgNode;
        }
      }
    }
    if (startNode != NULL) {
      assert( find(m_orderedNodes->begin(), m_orderedNodes->end(), startNode) ==
          m_orderedNodes->end() );
      tempNodes.push_back(startNode);
      m_orderedNodes->push_back(startNode);
    }
//    for (DFGNode* dfgNode: nodes) {
//      if (find(m_orderedNodes->begin(), m_orderedNodes->end(), dfgNode) ==
//          m_orderedNodes->end()) {
//        tempNodes.push_back(dfgNode);
//        m_orderedNodes->push_back(dfgNode);
//        break;
//      }
//    }
    DFGNode* currentNode;
    while (tempNodes.size() != 0) {
      currentNode = tempNodes.back();
      list<DFGNode*>* succNodes = currentNode->getSuccNodes();
      bool canPop = true;
      for (DFGNode* succNode: *succNodes) {
        if (find(m_orderedNodes->begin(), m_orderedNodes->end(), succNode) ==
            m_orderedNodes->end()) {
          tempNodes.push_back(succNode);
          canPop = false;
          m_orderedNodes->push_back(succNode);
          break;
        }
      }
      if (canPop) {
        tempNodes.pop_back();
      }
    }
  }
  cout<<"\nordered nodes: \n";
  for (DFGNode* dfgNode: *m_orderedNodes) {
    cout<<dfgNode->getID()<<"  ";
  }
  cout<<"\n";
  assert(m_orderedNodes->size() == nodes.size());
  return m_orderedNodes;
}

list<DFGNode*>* DFG::getBFSOrderedNodes() {
  if (m_orderedNodes != NULL)
    return m_orderedNodes;
  m_orderedNodes = new list<DFGNode*>();
  list<DFGNode*> tempNodes;
  while (m_orderedNodes->size() < nodes.size()) {
    for (DFGNode* dfgNode: nodes) {
      if (find(m_orderedNodes->begin(), m_orderedNodes->end(), dfgNode) ==
            m_orderedNodes->end()) {
        tempNodes.push_back(dfgNode);
        m_orderedNodes->push_back(dfgNode);
        break;
      }
    }
    DFGNode* currentNode;
    while (tempNodes.size() != 0) {
      currentNode = tempNodes.front();
      tempNodes.pop_front();
      for (DFGNode* succNode: *currentNode->getSuccNodes()) {
        if (find(m_orderedNodes->begin(), m_orderedNodes->end(), succNode) ==
            m_orderedNodes->end()) {
          tempNodes.push_back(succNode);
          m_orderedNodes->push_back(succNode);
        }
      }
    }
  }
  cout<<"\nordered nodes: \n";
  for (DFGNode* dfgNode: *m_orderedNodes) {
    cout<<dfgNode->getID()<<"  ";
  }
  cout<<"\n";
  assert(m_orderedNodes->size() == nodes.size());
  return m_orderedNodes;
}

// extract DFG from specific function
void DFG::construct(Function& t_F) {

  m_DFGEdges.clear();
  nodes.clear();
  m_ctrlEdges.clear();

  int nodeID = 0;
  int ctrlEdgeID = 0;
  int dfgEdgeID = 0;

  cout<<"*** current function: "<<t_F.getName().str()<<"\n";

  // FIXME: eleminate duplicated edges.
  for (Function::iterator BB=t_F.begin(), BEnd=t_F.end();
      BB!=BEnd; ++BB) {
    BasicBlock *curBB = &*BB;
    errs()<<"*** current basic block: "<<*curBB->begin()<<"\n";
    for (BasicBlock* sucBB : successors(curBB)) {
      errs()<<"   ****** succ bb: "<<*sucBB->begin()<<"\n";
    }

    string curBBName = curBB->getName().str();

     // Construct DFG nodes.
    for (BasicBlock::iterator II=curBB->begin(),
        IEnd=curBB->end(); II!=IEnd; ++II) {
      Instruction* curII = &*II;

      // Ignore this IR if it is out of the scope.
      if (shouldIgnore(curII)) {
        errs()<<*curII<<" *** ignored by pass due to that the BB is out "<<
            "of the scope (target loop)\n";
        continue;
      }
      errs()<<*curII;
      DFGNode* dfgNode;
      if (hasNode(curII)) {
        dfgNode = getNode(curII);
      } else {
        dfgNode = new DFGNode(nodeID++, m_precisionAware, curII, getValueName(curII), m_supportDVFS);
        nodes.push_back(dfgNode);
      }
      cout<<" (ID: "<<dfgNode->getID()<<")\n";
    }
    Instruction* terminator = curBB->getTerminator();

    if (shouldIgnore(terminator))
      continue;

//    DFGNode* dfgNodeTerm = new DFGNode(nodeID++, terminator, getValueName(terminator));
    for (BasicBlock* sucBB : successors(curBB)) {
      // TODO: get the live-in nodes rather than front() and connect them
      string sucBBName = sucBB->getName().str();
      errs()<<"[MMJ] "<<sucBB->getName()<<"\n";
      for (BasicBlock::iterator II=sucBB->begin(),
          IEnd=sucBB->end(); II!=IEnd; ++II) {
        Instruction* inst = &*II;

        // Ignore this IR if it is out of the scope.
        if (shouldIgnore(inst))
          continue;

        if (isLiveInInst(sucBB, inst)) {
          errs()<<" check inst: "<<*inst<<"\n";

          DFGNode* dfgNode;
          if (hasNode(inst)) {
            dfgNode = getNode(inst);
          } else {
            dfgNode = new DFGNode(nodeID++, m_precisionAware, inst, getValueName(inst), m_supportDVFS);
            nodes.push_back(dfgNode);
          }
    //      Instruction* first = &*(sucBB->begin());
    //      if (!getNode(inst)->isPhi()) {
    //
    //        cout<<"!!!!!!! [avoid as a phi] construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
    //        continue;
    //      }
    
          errs()<<"!!!!!!! construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
    
          // Construct contrl flow edges.
          DFGEdge* ctrlEdge;
          if (hasCtrlEdge(getNode(terminator), dfgNode)) {
            ctrlEdge = getCtrlEdge(getNode(terminator), dfgNode);
          }
          else {
            ctrlEdge = new DFGEdge(ctrlEdgeID++, getNode(terminator), dfgNode, true);
            m_ctrlEdges.push_back(ctrlEdge);
          }

        }
      }
    }
  }

//      Instruction* inst = &(sucBB->front());
////    for (Instruction* inst: sucBB) {
//      // Ignore this IR if it is out of the scope.
//      if (shouldIgnore(inst))
//        continue;
//      DFGNode* dfgNode;
//      if (hasNode(inst)) {
//        dfgNode = getNode(inst);
//      } else {
//        dfgNode = new DFGNode(nodeID++, inst, getValueName(inst));
//        nodes.push_back(dfgNode);
//      }
////      Instruction* first = &*(sucBB->begin());
////      if (!getNode(inst)->isPhi()) {
////
////        cout<<"!!!!!!! [avoid as a phi] construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
////        continue;
////      }
//
//      cout<<"!!!!!!! construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
//
//      // Construct contrl flow edges.
//      DFGEdge* ctrlEdge;
//      if (hasCtrlEdge(getNode(terminator), dfgNode)) {
//        ctrlEdge = getCtrlEdge(getNode(terminator), dfgNode);
//      }
//      else {
//        ctrlEdge = new DFGEdge(ctrlEdgeID++, getNode(terminator), dfgNode);
//        m_ctrlEdges.push_back(ctrlEdge);
//      }
//    }
//  }
 
//      for (BasicBlock::iterator II=sucBB->begin(),
//          IEnd=sucBB->end(); II!=IEnd; ++II) {
//        Instruction* inst = &*II;
////      for (Instruction* inst: sucBB) {
//        // Ignore this IR if it is out of the scope.
//        if (shouldIgnore(inst))
//          continue;
//        DFGNode* dfgNode;
//        if (hasNode(inst)) {
//          dfgNode = getNode(inst);
//        } else {
//          dfgNode = new DFGNode(nodeID++, inst, getValueName(inst));
//          nodes.push_back(dfgNode);
//        }
////        Instruction* first = &*(sucBB->begin());
//        if (!getNode(inst)->isPhi()) {
//
//          cout<<"!!!!!!! [avoid as a phi] construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
//          continue;
//        }
//
//        cout<<"!!!!!!! construct ctrl flow: "<<*terminator<<"->"<<*inst<<"\n";
//
//        // Construct contrl flow edges.
//        DFGEdge* ctrlEdge;
//        if (hasCtrlEdge(getNode(terminator), dfgNode)) {
//          ctrlEdge = getCtrlEdge(getNode(terminator), dfgNode);
//        }
//        else {
//          ctrlEdge = new DFGEdge(ctrlEdgeID++, getNode(terminator), dfgNode);
//          m_ctrlEdges.push_back(ctrlEdge);
//        }
//      }
//    }
//  }

//  // Construct contrl flow forward edges.
//  for (list<DFGNode*>::iterator nodeItr=nodes.begin();
//      nodeItr!=nodes.end(); ++nodeItr) {
//    list<DFGNode*>::iterator next = nodeItr;
//    ++next;
//    if (next != nodes.end()) {
//      DFGEdge* ctrlEdge;
//      if (hasCtrlEdge(*nodeItr, *next))
//        ctrlEdge = getCtrlEdge(*nodeItr, *next);
//      else {
//        ctrlEdge = new DFGEdge(ctrlEdgeID++, *nodeItr, *next);
//        m_ctrlEdges.push_back(ctrlEdge);
//      }
//    }
//  }

  // Construct data flow edges.
  for (DFGNode* node: nodes) {
//    nodes.push_back(Node(curII, getValueName(curII)));
    Instruction* curII = node->getInst();
    assert(node == getNode(curII));
    switch (curII->getOpcode()) {
      // The load/store instruction is special
      case llvm::Instruction::Load: {
        LoadInst* linst = dyn_cast<LoadInst>(curII);
        Value* loadValPtr = linst->getPointerOperand();

        // Parameter of the loop or the basic block, invisible in DFG.
        if (!hasNode(loadValPtr))
          break;
        DFGEdge* dfgEdge;
        if (hasDFGEdge(getNode(loadValPtr), node))
          dfgEdge = getDFGEdge(getNode(loadValPtr), node);
        else {
          dfgEdge = new DFGEdge(dfgEdgeID++, getNode(loadValPtr), node);
          m_DFGEdges.push_back(dfgEdge);
        }
//        getNode(loadValPtr)->setOutEdge(dfgEdge);
//        (*nodeItr)->setInEdge(dfgEdge);
        break;
      }
      case llvm::Instruction::Store: {
        StoreInst* sinst = dyn_cast<StoreInst>(curII);
        Value* storeValPtr = sinst->getPointerOperand();
        Value* storeVal = sinst->getValueOperand();
        DFGEdge* dfgEdge1;
        DFGEdge* dfgEdge2;

        // TODO: need to figure out storeVal and storeValPtr
        if (hasNode(storeVal)) {
          if (hasDFGEdge(getNode(storeVal), node))
            dfgEdge1 = getDFGEdge(getNode(storeVal), node);
          else {
            dfgEdge1 = new DFGEdge(dfgEdgeID++, getNode(storeVal), node);
            m_DFGEdges.push_back(dfgEdge1);
          }
//          getNode(storeVal)->setOutEdge(dfgEdge1);
//          (*nodeItr)->setInEdge(dfgEdge1);
        }
        if (hasNode(storeValPtr)) {
//          if (hasDFGEdge(*nodeItr, getNode(storeValPtr)))
          if (hasDFGEdge(getNode(storeValPtr), node))
//            dfgEdge2 = getDFGEdge(*nodeItr, getNode(storeValPtr));
            dfgEdge2 = getDFGEdge(getNode(storeValPtr), node);
          else {
//            dfgEdge2 = new DFGEdge(dfgEdgeID++, *nodeItr, getNode(storeValPtr));
            dfgEdge2 = new DFGEdge(dfgEdgeID++, getNode(storeValPtr), node);
            m_DFGEdges.push_back(dfgEdge2);
          }
//          getNode(storeValPtr)->setOutEdge(dfgEdge2);
//          (*nodeItr)->setInEdge(dfgEdge2);
//          (*nodeItr)->setOutEdge(dfgEdge2);
//          getNode(storeValPtr)->setInEdge(dfgEdge2);
        }
        break;
      }
      default: {
        for (Instruction::op_iterator op = curII->op_begin(), opEnd = curII->op_end(); op != opEnd; ++op) {
          Instruction* tempInst = dyn_cast<Instruction>(*op);
          if (tempInst and !shouldIgnore(tempInst)) {
//            if(node->isBranch()) {
//              cout<<"  the real branch's pred: "<<*tempInst<<"\n";
//              int numSuccs = tempInst->getNumSuccessors();
//            }
            DFGEdge* dfgEdge;
            if (hasNode(tempInst)) {
              if (hasDFGEdge(getNode(tempInst), node))
                dfgEdge = getDFGEdge(getNode(tempInst), node);
              else {
                dfgEdge = new DFGEdge(dfgEdgeID++, getNode(tempInst), node);
                m_DFGEdges.push_back(dfgEdge);
              }
//              getNode(tempInst)->setOutEdge(dfgEdge);
//              (*nodeItr)->setInEdge(dfgEdge);
            }
          } else {
            // Original Branch node will take three
            // predecessors (i.e., condi, true, false).
            if(!node->isBranch())
              node->addConst();
          } 
        }
//        if(node->isBranch()) {
//          int numSuccs = curII->getNumSuccessors();
//          cout<<"the succ of the branch: "<<*curII<<"; ("<<numSuccs<<")\n";
//          for(int i=0; i<numSuccs; ++i) {
//            BasicBlock* bb
//          }
//        }
        break;
      }
    }
  }
  connectDFGNodes();

  calculateCycles();

  // The mapping algorithm works on the DFG that is ordered in ASAP.
  // reorderInASAP();
  // The mapping algorithm works on the DFG that is ordered in ALAP.
  // reorderInALAP();
  // The mapping algorithm works on the DFG that is ordered along with the longest path.
  reorderInLongest();
  
}

// Reorder the DFG nodes in ASAP based on original sequential execution order.
void DFG::reorderInASAP() {

  list<DFGNode*> tempNodes;
  // The first node in the nodes is treated as the starting point (no 
  // matter it has predecessors or not).
  int maxLevel = 0;
  for (DFGNode* node: nodes) {
    int level = 0;
    for (DFGNode* predNode: *(node->getPredNodes())) {
      if (predNode->getID() < node->getID()) {
        if (level < predNode->getLevel() + 1) {
          level = predNode->getLevel() + 1;
        }
      }
    }
    node->setLevel(level);
    if (maxLevel < level) {
      maxLevel = level;
    }
  } 

  for (int l=0; l<maxLevel+1; ++l) {
    for (DFGNode* node: nodes) {
      if (node->getLevel() == l) {
        tempNodes.push_back(node);
      }
    }
  }

  nodes.clear();
  cout<<"[reorder DFG in ASAP]\n";
  for (DFGNode* node: tempNodes) {
    nodes.push_back(node);
    errs()<<"("<<node->getID()<<") "<<*(node->getInst())<<", level: "<<node->getLevel()<<"\n";
  }
}

bool DFG::isMinimumAndHasNotBeenVisited(set<DFGNode*>* t_visited, map<DFGNode*, int>* t_map, DFGNode* t_node) {
  if (t_visited->find(t_node) != t_visited->end()) {
    return false;
  }
  for (DFGNode* e_node: nodes) {
    if (e_node != t_node and t_visited->find(e_node) == t_visited->end() and (*t_map)[e_node] < (*t_map)[t_node]) {
      return false;
    }
  }
  return true;
}

// Reorder the DFG nodes based on the longest path.
void DFG::reorderInLongest() {
  list<DFGNode*>* longestPath = new list<DFGNode*>();
  list<DFGNode*>* currentPath = new list<DFGNode*>();
  set<DFGNode*>* visited = new set<DFGNode*>();
  map<DFGNode*, int> indegree;
  for (DFGNode* node: nodes) {
    indegree[node] = node->getPredNodes()->size();
    currentPath->clear();
    visited->clear();
    reorderDFS(visited, longestPath, currentPath, node);
  }

  visited->clear();
  int level = 0;
  for (DFGNode* node: *longestPath) {
    node->setLevel(level);
    visited->insert(node);
    //cout<<"check longest path node: "<<node->getID()<<endl;
    for (DFGNode* succNode: *(node->getSuccNodes())) {
      indegree[succNode] -= 1;
    }
    level += 1;
  }
  int maxLevel = level;

  while (visited->size() < nodes.size()) {
    for (DFGNode* node: nodes) {
      // if (visited->find(node) == visited->end() and indegree[node] <= 0) {
      if (isMinimumAndHasNotBeenVisited(visited, &indegree, node)) {
        level = 0;
        for (DFGNode* preNode: *(node->getPredNodes())) {
          if (level < preNode->getLevel() + 1) {
            level = preNode->getLevel() + 1;
          }
        }
        node->setLevel(level);
        visited->insert(node);
        for (DFGNode* succNode: *(node->getSuccNodes())) {
          indegree[succNode] -= 1;
        }
      }
    }
  }

  list<DFGNode*> tempNodes;
  for (int l=0; l<maxLevel+1; ++l) {
    for (DFGNode* node: nodes) {
      if (node->getLevel() == l) {
        tempNodes.push_back(node);
      }
    }
  }

  nodes.clear();
  cout<<"[reorder DFG along with the longest path]\n";
  for (DFGNode* node: tempNodes) {
    nodes.push_back(node);
    errs()<<"("<<node->getID()<<") "<<*(node->getInst())<<", level: "<<node->getLevel()<<"\n";
  }

}

void DFG::reorderDFS(set<DFGNode*>* t_visited, list<DFGNode*>* t_targetPath,
                     list<DFGNode*>* t_curPath, DFGNode* targetDFGNode) {

  t_visited->insert(targetDFGNode);
  t_curPath->push_back(targetDFGNode);

  // Update target longest path if current one is longer.
  if (t_curPath->size() > t_targetPath->size()) {
    t_targetPath->clear();
    for (DFGNode* node: *t_curPath) {
      t_targetPath->push_back(node);
    }
  }

  for (DFGNode* succNode: *(targetDFGNode->getSuccNodes())) {
    if (t_visited->find(succNode) == t_visited->end()) { // not visited yet
      reorderDFS(t_visited, t_targetPath, t_curPath, succNode);
      t_visited->erase(succNode);
      t_curPath->pop_back();
    }
  }

}


// Reorder the DFG nodes in ALAP based on original sequential execution order.
void DFG::reorderInALAP() {

  list<DFGNode*> tempNodes;
  // The last node in the nodes is treated as the end point (no 
  // matter it has successors or not).
  int maxLevel = 0;
  nodes.reverse();
  for (DFGNode* node: nodes) {
    int level = 0;
    for (DFGNode* succNode: *(node->getSuccNodes())) {
      if (succNode->getID() > node->getID()) {
        if (level < succNode->getLevel() + 1) {
          level = succNode->getLevel() + 1;
        }
      }
    }
    node->setLevel(level);
    if (maxLevel < level) {
      maxLevel = level;
    }
  } 

  for (DFGNode* node: nodes) {
    node->setLevel(maxLevel - node->getLevel());
  }

  for (int l=0; l<maxLevel+1; ++l) {
    for (DFGNode* node: nodes) {
      if (node->getLevel() == l) {
        tempNodes.push_back(node);
      }
    }
  }

  nodes.clear();
  cout<<"[reorder DFG in ALAP]\n";
  for (DFGNode* node: tempNodes) {
    nodes.push_back(node);
    errs()<<"("<<node->getID()<<") "<<*(node->getInst())<<", level: "<<node->getLevel()<<"\n";
  }
}

void DFG::initExecLatency(map<string, int>* t_execLatency) {
  set<string> targetOpt;
  for (map<string, int>::iterator iter=t_execLatency->begin();
      iter!=t_execLatency->end(); ++iter) {
    targetOpt.insert(iter->first);
  }
  for (DFGNode* node: nodes) {
    if (t_execLatency->find(node->getOpcodeName()) != t_execLatency->end()) {
      string opcodeName = node->getOpcodeName();
      node->setExecLatency((*t_execLatency)[opcodeName]);
      targetOpt.erase(opcodeName);
    }
  }
  if (!targetOpt.empty()) {
    cout<<"\033[0;31mPlease check the operations targeting multi-cycle execution in <param.json>:\"\033[0m";
    for (set<string>::iterator it = targetOpt.begin(); it != targetOpt.end(); ++it) {
      cout<<" "<<*it<<" "; // Note the "*" here
    }
    cout<<"\033[0;31m\".\033[0m"<<endl;
  }
}

void DFG::initPipelinedOpt(list<string>* t_pipelinedOpt) {
  set<string> targetOpt;
  for (string opt: *t_pipelinedOpt) {
    targetOpt.insert(opt);
  }
  for (DFGNode* node: nodes) {
    list<string>::iterator it;
    it = find(t_pipelinedOpt->begin(), t_pipelinedOpt->end(), node->getOpcodeName());
    if(it != t_pipelinedOpt->end()) {
      string opcodeName = node->getOpcodeName();
      node->setPipelinable();
      targetOpt.erase(opcodeName);
    }
  }
  if (!targetOpt.empty()) {
    cout<<"\033[0;31mPlease check the pipelinable operations in <param.json>:\"\033[0m";
    for (set<string>::iterator it = targetOpt.begin(); it != targetOpt.end(); ++it) {
      cout<<" "<<*it<<" "; // Note the "*" here
    }
    cout<<"\033[0;31m\".\033[0m"<<endl;
  }
}

bool DFG::isLiveInInst(BasicBlock* t_bb, Instruction* t_inst) {
  if (t_inst == &(t_bb->front())) {
    errs()<<"ctrl to: "<<*t_inst<<"; front: "<<(t_bb->front())<<"; ";
    return true;
  }
  for (Instruction::op_iterator op = t_inst->op_begin(), opEnd = t_inst->op_end(); op != opEnd; ++op) {
    Instruction* tempInst = dyn_cast<Instruction>(*op);
    if (tempInst and !containsInst(t_bb, tempInst)) {
      errs()<<"ctrl to: "<<*t_inst<<"; containsInst(t_bb, tempInst): "<<containsInst(t_bb, tempInst)<<"; ";
      return true;
    }
  }

  // The first (lower ID) IR with only in-block dependency is also treated as live-in.
  for (Instruction::op_iterator op = t_inst->op_begin(), opEnd = t_inst->op_end(); op != opEnd; ++op) {
    Instruction* tempInst = dyn_cast<Instruction>(*op);
    if (tempInst and getInstID(t_bb, t_inst) > getInstID(t_bb, tempInst)) {
      return false;
    }
  }

  errs()<<"ctrl to: "<<*t_inst<<"; ";
  return true;
}

bool DFG::containsInst(BasicBlock* t_bb, Instruction* t_inst) {

  for (BasicBlock::iterator II=t_bb->begin(),
       IEnd=t_bb->end(); II!=IEnd; ++II) {
    Instruction* inst = &*II;
    if ((inst) == (t_inst)) {
      return true;
    }
  }
  return false;
}

int DFG::getInstID(BasicBlock* t_bb, Instruction* t_inst) {

  int id = 0;
  for (BasicBlock::iterator II=t_bb->begin(),
       IEnd=t_bb->end(); II!=IEnd; ++II) {
    Instruction* inst = &*II;
    if ((inst) == (t_inst)) {
      return id;
    }
    id += 1;
  }
  // This never gonna happen.
  assert(false);
  return -1;
}

void DFG::connectDFGNodes() {
  for (DFGNode* node: nodes)
    node->cutEdges();

  // Incorporate ctrl flow into data flow.
  if (!m_CDFGFused) {
    for (DFGEdge* edge: m_ctrlEdges) {
      m_DFGEdges.push_back(edge);
    }
    m_CDFGFused = true;
  }

  for (DFGEdge* edge: m_DFGEdges) {
    DFGNode* left = edge->getSrc();
    DFGNode* right = edge->getDst();
    left->setOutEdge(edge);
    right->setInEdge(edge);
  }

//  for (DFGEdge* edge: m_ctrlEdges) {
//    DFGNode* left = edge->getSrc();
//    DFGNode* right = edge->getDst();
////    cout<<"... connectDFGNodes() for inst (left): "<<*(left->getInst())<<", (right): "<<*(right->getInst())<<"\n";
//    left->setOutEdge(edge);
//    right->setInEdge(edge);
//  }

}

void DFG::generateJSON() {
  ofstream jsonFile;
  jsonFile.open("dfg.json");
  jsonFile<<"[\n";
  int node_index = 0;
  int node_size = nodes.size();
  for (DFGNode* node: nodes) {
    jsonFile<<"  {\n";
    jsonFile<<"    \"fu\"         : \""<<node->getFuType()<<"\",\n";
    jsonFile<<"    \"id\"         : "<<node->getID()<<",\n";
    jsonFile<<"    \"org_opt\"    : \""<<node->getOpcodeName()<<"\",\n";
    jsonFile<<"    \"JSON_opt\"   : \""<<node->getJSONOpt()<<"\",\n";
    jsonFile<<"    \"in_const\"   : [";
    int const_size = node->getNumConst();
    for (int const_index=0; const_index < const_size; ++const_index) {
      jsonFile<<const_index;
      if (const_index < const_size - 1)
        jsonFile<<",";
    }
    jsonFile<<"],\n";
    jsonFile<<"    \"pre\"         : [";
    int in_size = node->getPredNodes()->size();
    int in_index = 0;
    for (DFGNode* predNode: *(node->getPredNodes())) {
      jsonFile<<predNode->getID();
      in_index += 1;
      if (in_index < in_size)
        jsonFile<<",";
    }
    jsonFile<<"],\n";
    jsonFile<<"    \"succ\"       : [[";
    int out_size = node->getSuccNodes()->size();
    int out_index = 0;
    for (DFGNode* succNode: *(node->getSuccNodes())) {
      jsonFile<<succNode->getID();
      out_index += 1;
      if (out_index < out_size)
        jsonFile<<",";
    }
    jsonFile<<"]]\n";
    node_index += 1;
    if (node_index < node_size)
      jsonFile<<"  },\n";
    else
      jsonFile<<"  }\n";
  }
  jsonFile<<"]\n";
  jsonFile.close();
}

void DFG::generateDot(Function &t_F, bool t_isTrimmedDemo) {

  error_code error;
//  sys::fs::OpenFlags F_Excl;
  string func_name = t_F.getName().str();
  string file_name = func_name + ".dot";
  std::ofstream file;
  file.open(file_name);
  // StringRef fileName(file_name);
  // raw_fd_ostream file(fileName, error, sys::fs::F_None);

  // TODO: support t_isTrimmedDemo = false, i.e., fix bugs of raw_fd_ostream
  assert(t_isTrimmedDemo == true);
  file << "digraph \"DFG for'" + string(t_F.getName().data()) + "\' function\" {\n";

  //Dump DFG nodes.
  for (DFGNode* node: nodes) {
//    if (dyn_cast<Instruction>((*node)->getInst())) {
    if (t_isTrimmedDemo) {
      file << "\tNode" << node->getID() << node->getOpcodeName() << "[shape=record, label=\"" << "(" << node->getID() << ") " << node->getOpcodeName() << "\"];\n";
    } else {
      // file << "\tNode" << node->getInst() << "[shape=record, label=\"" <<
      //     changeIns2Str(node->getInst()) << "\"];\n";
    }
  }
  /*
    if(dyn_cast<Instruction>(node->first))
      file << "\tNode" << node->first << "[shape=record, label=\"" << *(node->first) << "\"];\n";
      file << "\tNode" << (*node)->getInst() << "[shape=record, label=\"" << ((*node)->getID()) << "\"];\n";
    else {
      file << "\tNode" << (*node)->getInst() << "[shape=record, label=\"" << (*node)->getStringRef() << "\"];\n";
    }
            file << "\tNode" << node->first << "[shape=record, label=\"" << node->second << "\"];\n";
  */


  // Dump control flow.
  file << "edge [color=blue]" << "\n";
  for (DFGEdge* edge: m_ctrlEdges) {
    // Distinguish data and control flows. Don't show the ctrl flows that are optimzied out from the data flow optimization.
    if (find(m_DFGEdges.begin(), m_DFGEdges.end(), edge) != m_DFGEdges.end()) {
      if (t_isTrimmedDemo) {
        file << "\tNode" << edge->getSrc()->getID() << edge->getSrc()->getOpcodeName() << " -> Node" << edge->getDst()->getID() << edge->getDst()->getOpcodeName() << "\n";
      } else {
        // file << "\tNode" << edge->getSrc()->getInst() << " -> Node" << edge->getDst()->getInst() << "\n";
      }
    }
  }

  // Dump data flow.
  file << "edge [color=red]" << "\n";
  for (DFGEdge* edge: m_DFGEdges) {
    // Distinguish data and control flows. Make ctrl flow invisible.
    if (find(m_ctrlEdges.begin(), m_ctrlEdges.end(), edge) == m_ctrlEdges.end()) {
      if (t_isTrimmedDemo) {
        file << "\tNode" << edge->getSrc()->getID() << edge->getSrc()->getOpcodeName() << " -> Node" << edge->getDst()->getID() << edge->getDst()->getOpcodeName() << "\n";
      } else {
        // file << "\tNode" << edge->getSrc()->getInst() << " -> Node" << edge->getDst()->getInst() << "\n";
      }
    }
  }
//  cout << "Write data flow done.\n";
  file << "}\n";
  file.close();

}

void DFG::DFS_on_DFG(DFGNode* t_head, DFGNode* t_current,
    list<DFGNode*>* t_visitedNodes, list<DFGEdge*>* t_erasedEdges,
    list<DFGEdge*>* t_currentCycle, list<list<DFGEdge*>*>* t_cycles) {
  for (DFGEdge* edge: m_DFGEdges) {
    if (find(t_erasedEdges->begin(), t_erasedEdges->end(), edge) != t_erasedEdges->end())
      continue;
    // check whether the IR is equal
    if (edge->getSrc() == t_current) {
      // skip the visited nodes/edges:
      if (find(t_currentCycle->begin(), t_currentCycle->end(), edge) != t_currentCycle->end()) {
        continue;
      }
      t_currentCycle->push_back(edge);

//      cout << ".. add current cycle edge: {" << *edge->getSrc()->getInst() << "  } -> {"<< *edge->getDst()->getInst() << "  } ("<<edge->getSrc()->getID()<<" -> "<<edge->getDst()->getID()<<")\n";
      if (edge->getDst() == t_head) {
        cout << "==================================\n";
        errs() << "[detected one cycle] head: "<<*(t_head->getInst())<<"\n";
        list<DFGEdge*>* temp_cycle = new list<DFGEdge*>();
        for (DFGEdge* currentEdge: *t_currentCycle) {
          temp_cycle->push_back(currentEdge);
          // break the cycle to avoid future repeated detection
          errs() << "cycle edge: {" << *(currentEdge)->getSrc()->getInst() << "  } -> {"<< *(currentEdge)->getDst()->getInst() << "  } ("<<currentEdge->getSrc()->getID()<<" -> "<<currentEdge->getDst()->getID()<<")\n";
        }
        t_erasedEdges->push_back(edge);
        t_cycles->push_back(temp_cycle);
        t_currentCycle->remove(edge);
      } else {
        if (find(t_visitedNodes->begin(), t_visitedNodes->end(), edge->getDst()) == t_visitedNodes->end()) {
          t_visitedNodes->push_back(edge->getDst());
          // Only continue when the path size is less than the node count.
          if (t_currentCycle->size() <= nodes.size()) {
            DFS_on_DFG(t_head, edge->getDst(), t_visitedNodes, t_erasedEdges, t_currentCycle, t_cycles);
          }
        } else {
          t_currentCycle->remove(edge);
        }
      }
    }
  }
  if (t_currentCycle->size()!=0) {
    t_currentCycle->pop_back();
  }
}

list<list<DFGEdge*>*>* DFG::calculateCycles() {
  list<list<DFGEdge*>*>* cycleLists = new list<list<DFGEdge*>*>();
  list<DFGEdge*>* currentCycle = new list<DFGEdge*>();
  list<DFGNode*>* visitedNodes = new list<DFGNode*>();
  list<DFGEdge*>* erasedEdges = new list<DFGEdge*>();
  cycleLists->clear();
  for (DFGNode* node: nodes) {
    currentCycle->clear();
    visitedNodes->clear();
    visitedNodes->push_back(node);
    DFS_on_DFG(node, node, visitedNodes, erasedEdges, currentCycle, cycleLists);
  }
  int cycleID = 0;
  m_cycleNodeLists->clear();
  for (list<DFGEdge*>* cycle: *cycleLists) {
    list<DFGNode*>* nodeCycle = new list<DFGNode*>();
    for (DFGEdge* edge: *cycle) {
      edge->getDst()->setCritical();
      edge->getDst()->addCycleID(cycleID);
      nodeCycle->push_back(edge->getDst());
    }
    m_cycleNodeLists->push_back(nodeCycle);
    cycleID += 1;
  }
  return cycleLists;
}

list<list<DFGNode*>*>* DFG::getCycleLists() {
  return m_cycleNodeLists;
}

void DFG::showOpcodeDistribution() {

  map<string, int> opcodeMap;
  for (DFGNode* node: nodes) {
    opcodeMap[node->getOpcodeName()] += 1;
  }
  for (map<string, int>::iterator opcodeItr=opcodeMap.begin();
      opcodeItr!=opcodeMap.end(); ++opcodeItr) {
    cout << (*opcodeItr).first << " : " << (*opcodeItr).second << "\n";
  }
  int simdNodeCount = 0;
  for (DFGNode* node: nodes) {
    if (node->isVectorized()) {
      simdNodeCount++;
    }
  }    
  cout << "DFG node count: "<<nodes.size()<<"; DFG edge count: "<<m_DFGEdges.size()<<"; SIMD node count: "<<simdNodeCount<<"\n";
}

int DFG::getID(DFGNode* t_node) {
  int index = 0;
  return t_node->getID();
}

DFGNode* DFG::getNode(Value* t_value) {
  for (DFGNode* node: nodes) {
    if (node->getInst() == t_value) {
      return node;
    }
  }
  assert("ERROR cannot find the corresponding DFG node.");
  return NULL;
}

bool DFG::hasNode(Value* t_value) {
  for (DFGNode* node: nodes) {
    if (node->getInst() == t_value) {
      return true;
    }
  }
  return false;
}

DFGEdge* DFG::getCtrlEdge(DFGNode* t_src, DFGNode* t_dst) {
  for (DFGEdge* edge: m_ctrlEdges) {
    if (edge->getSrc() == t_src and
        edge->getDst() == t_dst) {
      return edge;
    }
  }
  assert("ERROR cannot find the corresponding Ctrl edge.");
  return NULL;
}

bool DFG::hasCtrlEdge(DFGNode* t_src, DFGNode* t_dst) {
  for (DFGEdge* edge: m_ctrlEdges) {
    if (edge->getSrc() == t_src and
        edge->getDst() == t_dst) {
      return true;
    }
  }
  return false;
}

DFGEdge* DFG::getDFGEdge(DFGNode* t_src, DFGNode* t_dst) {
  for (DFGEdge* edge: m_DFGEdges) {
    if (edge->getSrc() == t_src and
        edge->getDst() == t_dst) {
      return edge;
    }

  }
  assert("ERROR cannot find the corresponding DFG edge.");
  return NULL;
}

void DFG::replaceDFGEdge(DFGNode* t_old_src, DFGNode* t_old_dst,
                         DFGNode* t_new_src, DFGNode* t_new_dst) {
  DFGEdge* target = NULL;
  cout<<"replace edge: [delete] "<<t_old_src->getID()<<"->"<<t_old_dst->getID()<<" [new] "<<t_new_src->getID()<<"->"<<t_new_dst->getID()<<"\n";
  for (DFGEdge* edge: m_DFGEdges) {
    if (edge->getSrc() == t_old_src and
        edge->getDst() == t_old_dst) {
      target = edge;
      break;
    }
  }
  if (target == NULL) {
    cout << "ERROR cannot find the corresponding DFG edge\n";
    assert("ERROR cannot find the corresponding DFG edge.");   
    return;
  }
  m_DFGEdges.remove(target);
  // Keeps the ctrl property of the original edge on the newly added edge.
  DFGEdge* newEdge = new DFGEdge(target->getID(), t_new_src, t_new_dst, target->isCtrlEdge());
  m_DFGEdges.push_back(newEdge);
  if (newEdge->isCtrlEdge()){
    m_ctrlEdges.push_back(newEdge);
  }
}

// used for the case of tuning division patterns
void DFG::replaceMultipleDFGEdge(DFGNode* t_old_src, DFGNode* t_old_dst,
                         DFGNode** t_new_src, DFGNode** t_new_dst) {
  cout << "replace multiple dfg edges" << "\n";
  DFGEdge* target = NULL;
  cout<<"replace edge: [delete] "<<t_old_src->getID()<<"->"<<t_old_dst->getID()<<"\n";
  for (DFGEdge* edge: m_DFGEdges) {
    if (edge->getSrc() == t_old_src and
        edge->getDst() == t_old_dst) {
      target = edge;
      break;
    }
  }
  if (target == NULL) {
    cout << "ERROR cannot find the corresponding DFG edge\n";
    return;
  }
  int dfgEdgeID = m_DFGEdges.size();
  m_DFGEdges.remove(target);
  // Keeps the ctrl property of the original edge on the newly added edge.
  for (int i = 0; i < m_vectorFactorForIdiv; i++) {
    DFGEdge* newEdge;
    if (!i) {
      newEdge = new DFGEdge(target->getID(), t_new_src[i], t_new_dst[i], target->isCtrlEdge());
    }
    else {
      newEdge = new DFGEdge(dfgEdgeID++, t_new_src[i], t_new_dst[i], target->isCtrlEdge());
    }
    m_DFGEdges.push_back(newEdge);
    if (newEdge->isCtrlEdge()){
      m_ctrlEdges.push_back(newEdge);
    }
  }
}

void DFG::deleteDFGEdge(DFGNode* t_src, DFGNode* t_dst) {
  if (!hasDFGEdge(t_src, t_dst)) return;
  m_DFGEdges.remove(getDFGEdge(t_src, t_dst));
}

bool DFG::hasDFGEdge(DFGNode* t_src, DFGNode* t_dst) {
  for (DFGEdge* edge: m_DFGEdges) {
    if (edge->getSrc() == t_src and
        edge->getDst() == t_dst) {
      return true;
    }
  }
  return false;
}

string DFG::changeIns2Str(Instruction* t_ins) {
  string temp_str;
  raw_string_ostream os(temp_str);
  t_ins->print(os);
  return os.str();
}

//get value's name or inst's content
StringRef DFG::getValueName(Value* t_value) {
  string temp_result = "val";
  if (t_value->getName().empty()) {
    temp_result += to_string(m_num);
    m_num++;
  }
  else {
    temp_result = t_value->getName().str();
  }
  StringRef result(temp_result);
//  cout << "" << result;
  return result;
}

int DFG::getNodeCount() {
  return nodes.size();
}

void DFG::tuneForBitcast() {
  list<DFGNode*> unnecessaryDFGNodes;
  list<DFGEdge*> replaceDFGEdges;
  list<DFGEdge*> newDFGEdges;
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isBitcast()) {
      unnecessaryDFGNodes.push_back(dfgNode);
      list<DFGNode*>* predNodes = dfgNode->getPredNodes();
      for (DFGNode* predNode: *predNodes) {
        replaceDFGEdges.push_back(getDFGEdge(predNode, dfgNode));
      }
      list<DFGNode*>* succNodes = dfgNode->getSuccNodes();
      for (DFGNode* succNode: *succNodes) {
        replaceDFGEdges.push_back(getDFGEdge(dfgNode, succNode));
        for (DFGNode* predNode: *predNodes) {
          DFGEdge* bypassDFGEdge = new DFGEdge(predNode->getID(),
              predNode, succNode);
          newDFGEdges.push_back(bypassDFGEdge);
        }
      }
    }
  }

  for (DFGNode* dfgNode: unnecessaryDFGNodes)
    nodes.remove(dfgNode);

  for (DFGEdge* dfgEdge: replaceDFGEdges)
    m_DFGEdges.remove(dfgEdge);

  for (DFGEdge* dfgEdge: newDFGEdges)
    m_DFGEdges.push_back(dfgEdge);

  connectDFGNodes();
}

void DFG::tuneForLoad() {
  list<DFGNode*> unnecessaryDFGNodes;
  list<DFGEdge*> removeDFGEdges;
  list<DFGEdge*> newDFGEdges;
  for (DFGNode* dfgNode: nodes) {
    if (dfgNode->isGetptr()) {
      list<DFGNode*>* succNodes = dfgNode->getSuccNodes();
      DFGNode* firstLoadNode = NULL;
      for (DFGNode* succNode: *succNodes) {
        if (firstLoadNode == NULL and succNode->isLoad()) {
          firstLoadNode = succNode;
        } else if (firstLoadNode != NULL and succNode->isLoad()) {
          unnecessaryDFGNodes.push_back(succNode);
          removeDFGEdges.push_back(getDFGEdge(dfgNode, succNode));
          for (DFGNode* succOfLoad: *(succNode->getSuccNodes())) {
            DFGEdge* removeEdge = getDFGEdge(succNode, succOfLoad);
            removeDFGEdges.push_back(removeEdge);
            DFGEdge* newDFGEdge = new DFGEdge(removeEdge->getID(),
                firstLoadNode, succOfLoad);
            newDFGEdges.push_back(newDFGEdge);
          }
        }
      }
    }
  }

  for (DFGNode* dfgNode: unnecessaryDFGNodes)
    nodes.remove(dfgNode);

  for (DFGEdge* dfgEdge: removeDFGEdges)
    m_DFGEdges.remove(dfgEdge);

  for (DFGEdge* dfgEdge: newDFGEdges)
    m_DFGEdges.push_back(dfgEdge);

  connectDFGNodes();
}

// This is necessary to handle the control flow.
// Each one would have their own implementation about control
// flow handling. We simply connect 'br' to the entry ('phi')
// of the corresponding basic blocks (w/o including additional
// DFG nodes).
void DFG::tuneForBranch() {
  list<DFGNode*> processedDFGBrNodes;
  list<DFGEdge*> replaceDFGEdges;
  list<DFGEdge*> newBrDFGEdges;
  int newDFGEdgeID = m_DFGEdges.size();
  for (DFGEdge* dfgEdge: m_ctrlEdges) {
    DFGNode* left = dfgEdge->getSrc();
    DFGNode* right = dfgEdge->getDst();
    assert(left->isBranch());
    assert(right->isPhi());
    if (find(processedDFGBrNodes.begin(), processedDFGBrNodes.end(), left) ==
        processedDFGBrNodes.end()) {
      processedDFGBrNodes.push_back(left);
    } else {
      DFGNode* newDFGBrNode = new DFGNode(nodes.size(), m_precisionAware, left->getInst(),
          getValueName(left->getInst()), m_supportDVFS);
      for (DFGNode* predDFGNode: *(left->getPredNodes())) {
        DFGEdge* newDFGBrEdge = new DFGEdge(newDFGEdgeID++,
            predDFGNode, newDFGBrNode);
        m_DFGEdges.push_back(newDFGBrEdge);
      }
      nodes.push_back(newDFGBrNode);
      left = newDFGBrNode;
    }
    list<DFGNode*>* predNodes = right->getPredNodes();
    for (DFGNode* predNode: *predNodes) {
      DFGEdge* replaceDFGEdge = getDFGEdge(predNode, right);
      DFGEdge* brDataDFGEdge = new DFGEdge(replaceDFGEdge->getID(), predNode, left);
      DFGEdge* brCtrlDFGEdge = new DFGEdge(newDFGEdgeID++, left, right);
      // FIXME: Only consider one predecessor for 'phi' node for now.
      //        Need to care about true/false and make proper connection.
      replaceDFGEdges.push_back(replaceDFGEdge);
      newBrDFGEdges.push_back(brDataDFGEdge);
      newBrDFGEdges.push_back(brCtrlDFGEdge);
      break;
    }
  }
  for (DFGEdge* dfgEdge: replaceDFGEdges) {
    m_DFGEdges.remove(dfgEdge);
  }
  for (DFGEdge* dfgEdge: newBrDFGEdges) {
    m_DFGEdges.push_back(dfgEdge);
  }

  connectDFGNodes();
//    DFGEdge* brCtrlDFGEdge = new DFGEdge(m_DFGEdges.size(), left, right);
//    DFGEdge* replaceDFGEdge;
//    for (list<DFGNode*>::iterator predNodeItr=predNodes->begin();
//        predNodeItr!=predNodes->end(); ++predNodeItr) {
//      DFGNode* predNode = *predNodeItr;
//      list<DFGNode*>* visitedNodes = new list<DFGNode*>();
//      // Found one predNode is one the same control/data path as the 'br'.
//      if (searchDFS(left, predNode, visitedNodes)) {
//        replaceDFGEdge = getDFGEdge(predNode, right);
//        DFGEdge* brDataDFGEdge = new DFGEdge(replaceDFGEdge->getID(), predNode, left);
//        m_DFGEdges.remove(replaceDFGEdge);
//        m_DFGEdges.push_back(brDataDFGEdge);
//        break;
//      }
//    }
//    m_DFGEdges.push_back(brCtrlDFGEdge);
//  }
}

void DFG::trimForStandalone() {
  list<DFGNode*> removeNodes;
  for (DFGNode* dfgNode: nodes)
    if (dfgNode->getPredNodes()->size() == 0 and
        dfgNode->getSuccNodes()->size() == 0)
      removeNodes.push_back(dfgNode);

  for (DFGNode* dfgNode: removeNodes)
    nodes.remove(dfgNode);
}

bool DFG::searchDFS(DFGNode* t_target, DFGNode* t_head,
    list<DFGNode*>* t_visitedNodes) {
  for (DFGNode* succNode: *t_head->getSuccNodes()) {
    if (t_target == succNode) {
      return true;
    }
    // succNode is not yet visited.
    if (find(t_visitedNodes->begin(), t_visitedNodes->end(), succNode) ==
          t_visitedNodes->end()) {
      t_visitedNodes->push_back(succNode);
      if (searchDFS(t_target, succNode, t_visitedNodes)) {
        return true;
      }
    }
  }
  return false;
}

// TODO: This is necessary for inter-iteration data dependency
//       checking (ld/st dependency analysis on base address).
void DFG::detectMemDataDependency() {

}

// TODO: Certain opcode can be eliminated, such as bitcast, etc.
void DFG::eliminateOpcode(string t_opcodeName) {

}

