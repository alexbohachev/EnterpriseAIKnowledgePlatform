"""Explicit LangGraph state machine: authorize/retrieve -> grounded generation.

Stages are separately inspectable; actual context/ACL checks live in QueryEngine.
If LangGraph is absent the deployed endpoint fails closed with HTTP 503.
"""
from __future__ import annotations
from typing import TypedDict
from .query import QueryEngine, QueryResult
from .backends import BackendUnavailable


class GraphState(TypedDict, total=False):
    user_id: str
    question: str
    result: QueryResult
    items: list[dict]


def build_langgraph(engine: QueryEngine, session, user, observer=None):
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError as exc:
        raise BackendUnavailable('LangGraph missing: install project dependencies') from exc
    # Auditable 3-node graph: input gate -> ACL-filtered retrieval -> generation/ACL recheck.
    def gate(state: GraphState):
        if not state['question'].strip():
            raise ValueError('Question must not be blank')
        return {}

    def retrieve(state: GraphState):
        if observer is None:
            return {'items': engine.retrieve(session, user, state['question'])}
        with observer.stage('retrieval'):
            items = engine.retrieve(session, user, state['question'])
            observer.rag_excerpts.observe(len(items))
            return {'items': items}

    def generate(state: GraphState):
        if observer is None:
            return {'result': engine.generate(session, user, state['question'], state['items'])}
        with observer.stage('generation'):
            return {'result': engine.generate(session, user, state['question'], state['items'])}

    graph = StateGraph(GraphState)
    graph.add_node('input_gate', gate)
    graph.add_node('acl_filtered_retrieve', retrieve)
    graph.add_node('grounded_generate', generate)
    graph.add_edge(START, 'input_gate')
    graph.add_edge('input_gate', 'acl_filtered_retrieve')
    graph.add_edge('acl_filtered_retrieve', 'grounded_generate')
    graph.add_edge('grounded_generate', END)
    return graph.compile()
