# Build LangGraph routing between Triage, Diagnosis and Communication.
from langgraph.graph import END, START, StateGraph


# Route a successful communication-start result to Diagnosis or end the workflow.
def route_after_start(state):
    return 'diagnosis' if state.get('next_action') is None and state.get('category') != 'Other' else 'end'


# Connect the agent nodes and conditional routes, then compile the checkpointed graph.
def build_graph(state_schema, nodes, checkpointer=None):
    graph = StateGraph(state_schema)
    for name, handler in nodes.items():
        graph.add_node(name, handler)
    graph.add_node('prepare_routing', lambda state: {
        'retriage_requested': bool(state.get('retriage_requested') or state.get('next_action') == 'retriage')})
    graph.add_edge(START, 'prepare_routing')
    graph.add_edge('prepare_routing', 'triage')
    graph.add_conditional_edges('triage', lambda state:
        'communication' if state.get('next_action') in ('request_screenshot', 'request_information') else
        'start' if state.get('next_action') == 'diagnose' else 'end',
        {'communication': 'communication', 'start': 'communication_start', 'end': END})
    graph.add_conditional_edges('communication_start', route_after_start, {'diagnosis': 'diagnosis', 'end': END})
    graph.add_node('request_retriage', lambda state: {'retriage_requested': True})
    graph.add_edge('request_retriage', 'triage')
    graph.add_conditional_edges('diagnosis', lambda state:
        'triage' if state.get('next_action') == 'retriage' else
        'communication' if state.get('next_action') == 'request_information' else 'end',
        {'triage': 'request_retriage', 'communication': 'communication', 'end': END})
    graph.add_edge('communication', END)
    return graph.compile(checkpointer=checkpointer)
