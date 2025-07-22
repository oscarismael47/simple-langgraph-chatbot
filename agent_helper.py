import os
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
#from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
import streamlit as st

# Load secrets from Streamlit's secrets management
GROQ_API_KEY = st.secrets["GROQ-LMM"]["API_KEY"]
GROQ_MODEL = st.secrets["GROQ-LMM"]["MODEL"]
TAVILY_API_KEY = st.secrets["TAVILY"]["API_KEY"]  


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add] # Annoted means that new messages are added to  messages list
    input: str # the new values overrides the existing value of input

class Agent:
    def __init__(self, system="You are a helpful assistant. "):        
        
        system += " You have access to a search tool named 'tavily_search' Do not call tools unless specified in the tool list."
        model = ChatGroq(model=GROQ_MODEL,api_key=GROQ_API_KEY)

        tool = TavilySearch(tavily_api_key=TAVILY_API_KEY,max_results=4) #increased number of results
        tools = [tool]  # List of tools to be used by the agent

        self.system = system
        checkpointer = InMemorySaver()
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm", 
            self.exists_action, # the function that determines which node to go to next
            {True: "action", False: END} # if the function returns True, go to action, otherwise end the graph
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile(checkpointer=checkpointer)
        png = self.graph.get_graph().draw_mermaid_png()
        #with open("03_agent_with_memory.png", "wb") as f:
        #    f.write(png)
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools) # the llm knows that can use these tools, and how to use them
    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        return len(result.tool_calls) > 0
    
    def call_openai(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages': [message]}
    
    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            if not t['name'] in self.tools:      # check for bad tool name from LLM
                print("\n ....bad tool name....")
                result = "bad tool name, retry"  # instruct LLM to retry if bad
            else:
                result = self.tools[t['name']].invoke(t['args'])
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}
    
    def invoke(self, message, thread_id=None):
        messages = [HumanMessage(content=message)]
        result = self.graph.invoke({"messages": messages},
                                    {"configurable": {"thread_id": thread_id}})
        answer = result['messages'][-1].content
        return answer

if __name__ == "__main__":
    abot = Agent()
    thread_id = "1"  # This can be used to maintain context across multiple interactions
    user_message = input("Human: ")

    while user_message.lower() != "exit":
        ai_response = abot.invoke(user_message, thread_id=thread_id)
        print(f"AI: {ai_response}")
        user_message = input("Human: ")