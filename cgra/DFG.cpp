/*
 * ======================================================================
 * DFG.cpp
 * ======================================================================
 * DFG implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "DFG.h"

DFG::DFG(Function &F)
{
  this->num = 0;
  construct(F);
}

string DFG::changeIns2Str(Instruction* ins)
{
  string temp_str;
  raw_string_ostream os(temp_str);
  ins->print(os);
  return os.str();
}

//get value's name or inst's content
StringRef DFG::getValueName(Value* v)
{
  string temp_result = "val";
  if (v->getName().empty())
  {
    temp_result += to_string(num);
    num++;
  }
  else {
    temp_result = v->getName().str();
  }
  StringRef result(temp_result);
//  errs() << "" << result;
  return result;
}

int DFG::getNodeCount()
{
  return nodes.size();
}

// extract DFG from specific function
void DFG::construct(Function &F)
{
  error_code error;
//  sys::fs::OpenFlags F_Excl;
  StringRef fileName(F.getName().str() + ".dot");
  raw_fd_ostream file(fileName, error, sys::fs::F_None);
  dfg_edges.clear();
  nodes.clear();
  inst_edges.clear();

  for (Function::iterator BB=F.begin(), BEnd=F.end(); BB!=BEnd; ++BB) {
    BasicBlock *curBB = &*BB;
    for (BasicBlock::iterator II=curBB->begin(), IEnd=curBB->end(); II!=IEnd; ++II){
      Instruction* curII = &*II;
      curII->dump();
      switch (curII->getOpcode())
      {
            //load/store is special
        case llvm::Instruction::Load:
        {
          LoadInst* linst = dyn_cast<LoadInst>(curII);
          Value* loadValPtr = linst->getPointerOperand();
          dfg_edges.push_back(Edge(Node(loadValPtr, getValueName(loadValPtr)), Node(curII, getValueName(curII))));
          break;
        }
        case llvm::Instruction::Store: {
          StoreInst* sinst = dyn_cast<StoreInst>(curII);
          Value* storeValPtr = sinst->getPointerOperand();
          Value* storeVal = sinst->getValueOperand();
          dfg_edges.push_back(Edge(Node(storeVal, getValueName(storeVal)), Node(curII, getValueName(curII))));
          dfg_edges.push_back(Edge(Node(curII, getValueName(curII)), Node(storeValPtr, getValueName(storeValPtr))));
          break;
        }
        default: {
          for (Instruction::op_iterator op = curII->op_begin(), opEnd = curII->op_end(); op != opEnd; ++op)
          {
            Instruction* tempIns;
            if (dyn_cast<Instruction>(*op))
            {
                    dfg_edges.push_back(Edge(Node(op->get(), getValueName(op->get())), Node(curII, getValueName(curII))));
            }
          }
          break;
        }
      }
      BasicBlock::iterator next = II;
      //errs() << curII << "\n";
      nodes.push_back(Node(curII, getValueName(curII)));
      ++next;
      if (next != IEnd) {
        inst_edges.push_back(Edge(Node(curII, getValueName(curII)), Node(&*next, getValueName(&*next))));
      }
    }

    Instruction* terminator = curBB->getTerminator();
    for (BasicBlock* sucBB : successors(curBB)) {
      Instruction* first = &*(sucBB->begin());
      inst_edges.push_back(Edge(Node(terminator, getValueName(terminator)), Node(first, getValueName(first))));
    }
  }
  //errs() << "Write\n";
  file << "digraph \"DFG for'" + F.getName() + "\' function\" {\n";
  //errs() << "Write DFG\n";
  //dump nodes
  for (list<Node>::iterator node=nodes.begin(), node_end=nodes.end(); node!=node_end; ++node) {
    //errs() << "Node First:" << node->first << "\n";
    //errs() << "Node Second:" << node-> second << "\n";
    if(dyn_cast<Instruction>(node->first))
            file << "\tNode" << node->first << "[shape=record, label=\"" << *(node->first) << "\"];\n";
    else
            file << "\tNode" << node->first << "[shape=record, label=\"" << node->second << "\"];\n";
  }
  //errs() << "Write Done\n";
  //dump insts with ordering
  for (list<Edge>::iterator edge = inst_edges.begin(), edge_end = inst_edges.end(); edge != edge_end; ++edge) {
    file << "\tNode" << edge->first.first << " -> Node" << edge->second.first << "\n";
  }
  //dump data flow
  file << "edge [color=red]" << "\n";
  for (list<Edge>::iterator edge=dfg_edges.begin(), edge_end=dfg_edges.end(); edge!=edge_end; ++edge) {
    file << "\tNode" << edge->first.first << " -> Node" << edge->second.first << "\n";
  }
  errs() << "Write Done\n";
  file << "}\n";
  file.close();
//  return false;
}

void DFG::DFS_on_DFG(Node head, Node current, list<Edge> *erased_edges,
                     list<Edge> *current_cycle, list<list<Edge>> *cycles) 
{
  int times = 0;
  for(list<Edge>::iterator edge=dfg_edges.begin(); edge!=dfg_edges.end(); ++edge)
  {
    times++;
    if(find(erased_edges->begin(), erased_edges->end(), *edge) != erased_edges->end())
      continue;
    // check whether to IR is equal
    if(edge->first.first == current.first)
    {
      // skip the visited nodes/edges:
      if(find(current_cycle->begin(), current_cycle->end(), *edge) != current_cycle->end())
      {
        continue;
      }
      current_cycle->push_back(*edge);
//      errs() << "push_back: (first) " << *edge->first.first << "; (second) "<< *edge->second.first << "; head: " << *head.first << "\n";
      if(edge->second == head)
      {
        errs() << "==================================\n";
        errs() << "[detected one cycle]\n";
        list<Edge> temp_cycle;
        for(list<Edge>::iterator e=current_cycle->begin(); e!=current_cycle->end(); ++e)
        {
          temp_cycle.push_back(*e);
          // break the cycle to avoid future repeated detection
          errs() << "cycle edge: {" << *e->first.first << "  } -> {"<< *e->second.first << "  }\n";
        }
        erased_edges->push_back(*edge);
        cycles->push_back(temp_cycle);
      } else {
        DFS_on_DFG(head, edge->second, erased_edges, current_cycle, cycles);
      }
    }
  }
  if(current_cycle->size()!=0)
  {
    current_cycle->pop_back();
  }
}

list<list<DFG::Edge>> DFG::getCycles()
{
  list<list<Edge>> *cycle_lists = new list<list<Edge>>();
  list<Edge> *current_cycle = new list<Edge>();
  list<Edge> *erased_edges = new list<Edge>();
  cycle_lists->clear();
  for(list<Node>::iterator node=nodes.begin(); node!=nodes.end(); ++node)
  { 
    current_cycle->clear();  
    DFS_on_DFG(*node, *node, erased_edges, current_cycle, cycle_lists);
  }
  return *cycle_lists;
}

list<DFG::Node> DFG::getPredNodes(Node node)
{
  list<Node> predNodes;
  for(list<Edge>::iterator edge=dfg_edges.begin(); edge!=dfg_edges.end(); ++edge)
  {
    if(edge->second.first == node.first)
    {
      predNodes.push_back(edge->first);
    }
  }
  return predNodes;
}

int DFG::getID(Node t_node)
{
  int index = 0;
  for(list<Node>::iterator iter=nodes.begin(); iter!=nodes.end(); ++iter) {
    if((*iter).first == t_node.first) {
      return index;
    }
    ++index;
  }
  return -1;
}

