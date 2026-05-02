# Chapter 2: Routing

# 第 2 章：路由

## Routing Pattern Overview

## 路由模式概述

While sequential processing via prompt chaining is a foundational technique for executing deterministic, linear workflows with language models, its applicability is limited in scenarios requiring adaptive responses. Real-world agentic systems must often arbitrate between multiple potential actions based on contingent factors, such as the state of the environment, user input, or the outcome of a preceding operation. This capacity for dynamic decision-making, which governs the flow of control to different specialized functions, tools, or sub-processes, is achieved through a mechanism known as routing.

虽然通过提示词链进行顺序处理是使用语言模型执行确定性、线性工作流的基础技术，但在需要自适应响应的场景中，它的适用性会受到限制。现实世界的智能体系统必须经常根据偶然因素在多个潜在行动之间进行仲裁，例如环境状态、用户输入或前一操作的结果。这种控制流向不同专门函数、工具或子流程的动态决策能力，是通过一种称为路由的机制实现的。

Routing introduces conditional logic into an agent's operational framework, enabling a shift from a fixed execution path to a model where the agent dynamically evaluates specific criteria to select from a set of possible subsequent actions. This allows for more flexible and context-aware system behavior.

路由将条件逻辑引入智能体系统的操作框架，使其从固定的执行路径转变为这样一种模型：智能体动态评估特定标准，从一组可能的后续操作中进行选择。这使得系统行为更加灵活且具有上下文感知能力。

For instance, an agent designed for customer inquiries, when equipped with a routing function, can first classify an incoming query to determine the user's intent. Based on this classification, it can then direct the query to a specialized agent for direct question-answering, a database retrieval tool for account information, or an escalation procedure for complex issues, rather than defaulting to a single, predetermined response pathway.  Therefore, a more sophisticated agent using routing could:

例如，一个设计用于处理客户查询的智能体，在配备路由功能时，可以首先对传入查询进行分类以确定用户的意图。基于此分类，它可以将查询定向到专门的智能体进行直接问答、用于帐户信息的数据库检索工具，或用于复杂问题的升级流程，而不是默认使用单一的预定响应路径。因此，使用路由的更复杂智能体可以：

1. Analyze the user's query.  
2. **Route** the query based on its *intent*:  
   * If the intent is "check order status", route to a sub-agent or tool chain that interacts with the order database.  
   * If the intent is "product information", route to a sub-agent or chain that searches the product catalog.  
   * If the intent is "technical support", route to a different chain that accesses troubleshooting guides or escalates to a human.  
   * If the intent is unclear, route to a clarification sub-agent or prompt chain.

1. 分析用户的查询。
2. 基于其**意图**路由查询：
   * 如果意图是"检查订单状态"，路由到与订单数据库交互的子智能体或工具链。
   * 如果意图是"产品信息"，路由到搜索产品目录的子智能体或链。
   * 如果意图是"技术支持"，路由到访问故障排除指南或升级到人工的不同链。
   * 如果意图不清楚，路由到澄清子智能体或提示词链。

The core component of the Routing pattern is a mechanism that performs the evaluation and directs the flow. This mechanism can be implemented in several ways:

路由模式的核心组件是执行评估并指导流程的机制。这种机制可以通过几种方式实现：

* **LLM-based Routing:** The language model itself can be prompted to analyze the input and output a specific identifier or instruction that indicates the next step or destination. For example, a prompt might ask the LLM to "Analyze the following user query and output only the category: 'Order Status', 'Product Info', 'Technical Support', or 'Other'." The agentic system then reads this output and directs the workflow accordingly.  
* **Embedding-based Routing:** The input query can be converted into a vector embedding (see RAG, Chapter 14). This embedding is then compared to embeddings representing different routes or capabilities. The query is routed to the route whose embedding is most similar. This is useful for semantic routing, where the decision is based on the meaning of the input rather than just keywords.  
* **Rule-based Routing:** This involves using predefined rules or logic (e.g., if-else statements, switch cases) based on keywords, patterns, or structured data extracted from the input. This can be faster and more deterministic than LLM-based routing, but is less flexible for handling nuanced or novel inputs.  
* **Machine Learning Model-Based Routing**: it employs a discriminative model, such as a classifier, that has been specifically trained on a small corpus of labeled data to perform a routing task. While it shares conceptual similarities with embedding-based methods, its key characteristic is the supervised fine-tuning process, which adjusts the model's parameters to create a specialized routing function. This technique is distinct from LLM-based routing because the decision-making component is not a generative model executing a prompt at inference time. Instead, the routing logic is encoded within the fine-tuned model's learned weights. While LLMs may be used in a pre-processing step to generate synthetic data for augmenting the training set, they are not involved in the real-time routing decision itself.

* **基于 LLM 的路由：** 可以提示语言模型本身分析输入并输出指示下一步或目的地的特定标识符或指令。例如，提示词可能要求 LLM "分析以下用户查询并仅输出类别：'订单状态'、'产品信息'、'技术支持'或'其他'。"智能体系统然后读取此输出并相应地指导工作流。
* **基于嵌入的路由：** 输入查询可以转换为向量嵌入（参见第 14 章 RAG）。然后将此嵌入与代表不同路由或能力的嵌入进行比较。查询被路由到嵌入最相似的路由。这对于语义路由很有用，其中决策基于输入的含义而不仅仅是关键词。
* **基于规则的路由：** 这涉及使用基于关键词、模式或从输入中提取的结构化数据的预定义规则或逻辑（例如，if-else 语句、switch case）。这可以比基于 LLM 的路由更快、更具确定性，但在处理细微或新颖输入方面的灵活性较差。
* **基于机器学习模型的路由：** 它采用判别模型，例如分类器，该模型已经在小型标记数据语料库上专门训练以执行路由任务。虽然它与基于嵌入的方法在概念上有相似之处，但其关键特征是监督微调过程，该过程调整模型的参数以创建专门的路由功能。这种技术与基于 LLM 的路由不同，因为决策组件不是在推理时执行提示词的生成模型。相反，路由逻辑被编码在微调模型的学习权重中。虽然 LLM 可能在预处理步骤中用于生成合成数据以增强训练集，但它们不参与实时路由决策本身。

Routing mechanisms can be implemented at multiple junctures within an agent's operational cycle. They can be applied at the outset to classify a primary task, at intermediate points within a processing chain to determine a subsequent action, or during a subroutine to select the most appropriate tool from a given set.

路由机制可以在智能体系统的操作周期内的多个节点实现。它们可以在开始时应用以对主要任务进行分类，在处理链内的中间点应用以确定后续操作，或在子程序期间应用以从给定集合中选择最合适的工具。

Computational frameworks such as LangChain, LangGraph, and Google's Agent Developer Kit (ADK) provide explicit constructs for defining and managing such conditional logic. With its state-based graph architecture, LangGraph is particularly well-suited for complex routing scenarios where decisions are contingent upon the accumulated state of the entire system. Similarly, Google's ADK provides foundational components for structuring an agent's capabilities and interaction models, which serve as the basis for implementing routing logic. Within the execution environments provided by these frameworks, developers define the possible operational paths and the functions or model-based evaluations that dictate the transitions between nodes in the computational graph.

诸如 LangChain、LangGraph 和 Google 智能体开发工具包 (ADK) 等计算框架提供了用于定义和管理这种条件逻辑的显式构造。凭借其基于状态的图架构，LangGraph 特别适合复杂的路由场景，其中决策取决于整个系统的累积状态。类似地，Google 的 ADK 提供了用于构建智能体系统能力和交互模型的基础组件，这些组件作为实现路由逻辑的基础。在这些框架提供的执行环境中，开发人员定义可能的操作路径以及决定计算图中节点之间转换的函数或基于模型的评估。

The implementation of routing enables a system to move beyond deterministic sequential processing. It facilitates the development of more adaptive execution flows that can respond dynamically and appropriately to a wider range of inputs and state changes.

路由的实现使系统能够超越确定性顺序处理。它促进了更自适应的执行流的开发，可以动态且适当地响应更广泛的输入和状态变化。

## Practical Applications & Use Cases

## 实际应用与用例

The routing pattern is a critical control mechanism in the design of adaptive agentic systems, enabling them to dynamically alter their execution path in response to variable inputs and internal states. Its utility spans multiple domains by providing a necessary layer of conditional logic.

路由模式是自适应智能体系统设计中的关键控制机制，使它们能够动态改变其执行路径以响应可变输入和内部状态。它通过提供必要的条件逻辑层，在多个领域发挥作用。

In human-computer interaction, such as with virtual assistants or AI-driven tutors, routing is employed to interpret user intent. An initial analysis of a natural language query determines the most appropriate subsequent action, whether it is invoking a specific information retrieval tool, escalating to a human operator, or selecting the next module in a curriculum based on user performance. This allows the system to move beyond linear dialogue flows and respond contextually.

在人机交互中，例如虚拟助手或 AI 驱动的导师，路由用于解释用户意图。对自然语言查询的初始分析确定最合适的后续操作，无论是调用特定信息检索工具、升级到人工操作员，还是根据用户表现选择课程中的下一个模块。这使系统能够超越线性对话流并进行上下文响应。

Within automated data and document processing pipelines, routing serves as a classification and distribution function. Incoming data, such as emails, support tickets, or API payloads, is analyzed based on content, metadata, or format. The system then directs each item to a corresponding workflow, such as a sales lead ingestion process, a specific data transformation function for JSON or CSV formats, or an urgent issue escalation path.

在自动化数据和文档处理管道中，路由作为分类和分发功能。传入的数据，如电子邮件、支持工单或 API 有效载荷，根据内容、元数据或格式进行分析。然后系统将每个项目定向到相应的工作流，例如销售线索摄入流程、JSON 或 CSV 格式的特定数据转换函数，或紧急问题升级路径。

In complex systems involving multiple specialized tools or agents, routing acts as a high-level dispatcher. A research system composed of distinct agents for searching, summarizing, and analyzing information would use a router to assign tasks to the most suitable agent based on the current objective. Similarly, an AI coding assistant uses routing to identify the programming language and user's intent—to debug, explain, or translate—before passing a code snippet to the correct specialized tool.

在涉及多个专门工具或智能体的复杂系统中，路由充当高级调度器。由用于搜索、总结和分析信息的不同智能体组成的研究系统将使用路由器根据当前目标将任务分配给最合适的智能体。类似地，AI 编码助手使用路由来识别编程语言和用户意图——调试、解释或翻译——然后将代码片段传递给正确的专门工具。

Ultimately, routing provides the capacity for logical arbitration that is essential for creating functionally diverse and context-aware systems. It transforms an agent from a static executor of pre-defined sequences into a dynamic system that can make decisions about the most effective method for accomplishing a task under changing conditions.

最终，路由提供了创建功能多样化和上下文感知系统所必需的逻辑仲裁能力。它将智能体从预定义序列的静态执行器转变为可以在变化条件下就完成任务的最有效方法做出决策的动态系统。

## Hands-On Code Example (LangChain)

## 实操代码示例（LangChain）

Implementing routing in code involves defining the possible paths and the logic that decides which path to take. Frameworks like LangChain and LangGraph provide specific components and structures for this. LangGraph's state-based graph structure is particularly intuitive for visualizing and implementing routing logic.

在代码中实现路由涉及定义可能的路径和决定采取哪条路径的逻辑。像 LangChain 和 LangGraph 这样的框架为此提供了特定的组件和结构。LangGraph 基于状态的图结构对于可视化和实现路由逻辑特别直观。

This code demonstrates a simple agent-like system using LangChain and Google's Generative AI. It sets up a "coordinator" that routes user requests to different simulated "sub-agent" handlers based on the request's intent (booking, information, or unclear). The system uses a language model to classify the request and then delegates it to the appropriate handler function, simulating a basic delegation pattern often seen in multi-agent architectures.

此代码演示了使用 LangChain 和 Google 的生成式 AI 的简单类智能体系统。它设置了一个"协调器"，根据请求的意图（预订、信息或不清楚）将用户请求路由到不同的模拟"子智能体"处理程序。系统使用语言模型对请求进行分类，然后将其委托给适当的处理函数，模拟多智能体架构中常见的基本委托模式。

First, ensure you have the necessary libraries installed:

```bash
pip install langchain langgraph google-cloud-aiplatform langchain-google-genai google-adk deprecated pydantic
```

首先，确保您已安装必要的库：

You will also need to set up your environment with your API key for the language model you choose (e.g., OpenAI, Google Gemini, Anthropic).

您还需要使用您选择的语言模型的 API 密钥设置环境（例如，OpenAI、Google Gemini、Anthropic）。

```python
## Copyright (c) 2025 Marco Fago
## https://www.linkedin.com/in/marco-fago/
#
## This code is licensed under the MIT License.
## See the LICENSE file in the repository for the full license text.

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

## --- Configuration ---
## Ensure your API key environment variable is set (e.g., GOOGLE_API_KEY)
try:
   llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
   print(f"Language model initialized: {llm.model}")
except Exception as e:
   print(f"Error initializing language model: {e}")
   llm = None

## --- Define Simulated Sub-Agent Handlers (equivalent to ADK sub_agents) ---
def booking_handler(request: str) -> str:
   """Simulates the Booking Agent handling a request."""
   print("\n--- DELEGATING TO BOOKING HANDLER ---")
   return f"Booking Handler processed request: '{request}'. Result: Simulated booking action."

def info_handler(request: str) -> str:
   """Simulates the Info Agent handling a request."""
   print("\n--- DELEGATING TO INFO HANDLER ---")
   return f"Info Handler processed request: '{request}'. Result: Simulated information retrieval."

def unclear_handler(request: str) -> str:
   """Handles requests that couldn't be delegated."""
   print("\n--- HANDLING UNCLEAR REQUEST ---")
   return f"Coordinator could not delegate request: '{request}'. Please clarify."

## --- Define Coordinator Router Chain (equivalent to ADK coordinator's instruction) ---
## This chain decides which handler to delegate to.
coordinator_router_prompt = ChatPromptTemplate.from_messages([
   ("system", """Analyze the user's request and determine which specialist handler should process it.
   - If the request is related to booking flights or hotels,
       output 'booker'.
   - For all other general information questions, output 'info'.
   - If the request is unclear or doesn't fit either category,
       output 'unclear'.
   ONLY output one word: 'booker', 'info', or 'unclear'."""),
   ("user", "{request}")
])

if llm:
   coordinator_router_chain = coordinator_router_prompt | llm | StrOutputParser()

## --- Define the Delegation Logic (equivalent to ADK's Auto-Flow based on sub_agents) ---
## Use RunnableBranch to route based on the router chain's output.
## Define the branches for the RunnableBranch
branches = {
   "booker": RunnablePassthrough.assign(output=lambda x: booking_handler(x['request']['request'])),
   "info": RunnablePassthrough.assign(output=lambda x: info_handler(x['request']['request'])),
   "unclear": RunnablePassthrough.assign(output=lambda x: unclear_handler(x['request']['request'])),
}

## Create the RunnableBranch. It takes the output of the router chain
## and routes the original input ('request') to the corresponding handler.
delegation_branch = RunnableBranch(
   (lambda x: x['decision'].strip() == 'booker', branches["booker"]), # Added .strip()
   (lambda x: x['decision'].strip() == 'info', branches["info"]),     # Added .strip()
   branches["unclear"] # Default branch for 'unclear' or any other output
)

## Combine the router chain and the delegation branch into a single runnable
## The router chain's output ('decision') is passed along with the original input ('request')
## to the delegation_branch.
coordinator_agent = {
   "decision": coordinator_router_chain,
   "request": RunnablePassthrough()
} | delegation_branch | (lambda x: x['output']) # Extract the final output

## --- Example Usage ---
def main():
   if not llm:
       print("\nSkipping execution due to LLM initialization failure.")
       return

   print("--- Running with a booking request ---")
   request_a = "Book me a flight to London."
   result_a = coordinator_agent.invoke({"request": request_a})
   print(f"Final Result A: {result_a}")

   print("\n--- Running with an info request ---")
   request_b = "What is the capital of Italy?"
   result_b = coordinator_agent.invoke({"request": request_b})
   print(f"Final Result B: {result_b}")

   print("\n--- Running with an unclear request ---")
   request_c = "Tell me about quantum physics."
   result_c = coordinator_agent.invoke({"request": request_c})
   print(f"Final Result C: {result_c}")

if __name__ == "__main__":
   main()
```

As mentioned, this Python code constructs a simple agent-like system using the LangChain library and Google's Generative AI model, specifically gemini-2.5-flash. In detail, It defines three simulated sub-agent handlers: booking\_handler, info\_handler, and unclear\_handler, each designed to process specific types of requests. 

如上所述，这段 Python 代码使用 LangChain 库和 Google 的生成式 AI 模型（特别是 gemini-2.5-flash）构建了一个简单的类智能体系统。详细来说，它定义了三个模拟子智能体处理程序：booking_handler、info_handler 和 unclear_handler，每个都设计用于处理特定类型的请求。

A core component is the coordinator\_router\_chain, which utilizes a ChatPromptTemplate to instruct the language model to categorize incoming user requests into one of three categories: 'booker', 'info', or 'unclear'. The output of this router chain is then used by a RunnableBranch to delegate the original request to the corresponding handler function. The RunnableBranch checks the decision from the language model and directs the request data to either the booking\_handler, info\_handler, or unclear\_handler. The coordinator\_agent combines these components, first routing the request for a decision and then passing the request to the chosen handler. The final output is extracted from the handler's response. 

核心组件是 coordinator_router_chain，它利用 ChatPromptTemplate 指示语言模型将传入的用户请求分类为三个类别之一：'booker'、'info' 或 'unclear'。然后路由链的输出由 RunnableBranch 使用，将原始请求委托给相应的处理函数。RunnableBranch 检查来自语言模型的决策，并将请求数据定向到 booking_handler、info_handler 或 unclear_handler。coordinator_agent 结合了这些组件，首先路由请求以做出决策，然后将请求传递给选定的处理程序。最终输出从处理程序的响应中提取。

The main function demonstrates the system's usage with three example requests, showcasing how different inputs are routed and processed by the simulated agents. Error handling for language model initialization is included to ensure robustness. The code structure mimics a basic multi-agent framework where a central coordinator delegates tasks to specialized agents based on intent.

main 函数通过三个示例请求演示了系统的用法，展示了不同的输入如何被路由并由模拟智能体处理。包含了语言模型初始化的错误处理以确保健壮性。代码结构模仿了基本的多智能体框架，其中中央协调器根据意图将任务委托给专门的智能体。

## Hands-On Code Example (Google ADK)

## 实操代码示例（Google ADK）

The Agent Development Kit (ADK) is a framework for engineering agentic systems, providing a structured environment for defining an agent's capabilities and behaviours. In contrast to architectures based on explicit computational graphs, routing within the ADK paradigm is typically implemented by defining a discrete set of "tools" that represent the agent's functions. The selection of the appropriate tool in response to a user query is managed by the framework's internal logic, which leverages an underlying model to match user intent to the correct functional handler.

智能体开发工具包 (ADK) 是一个用于工程化智能体系统的框架，为定义智能体能力和行为提供了结构化环境。与基于显式计算图的架构相比，ADK 范式中的路由通常通过定义一组离散的"工具"来实现，这些工具代表智能体的功能。响应用户查询选择适当工具由框架的内部逻辑管理，该逻辑利用底层模型将用户意图与正确的功能处理程序匹配。

This Python code demonstrates an example of an Agent Development Kit (ADK) application using Google's ADK library. It sets up a "Coordinator" agent that routes user requests to specialized sub-agents ("Booker" for bookings and "Info" for general information) based on defined instructions. The sub-agents then use specific tools to simulate handling the requests, showcasing a basic delegation pattern within an agent system.

此 Python 代码演示了使用 Google ADK 库的智能体开发工具包 (ADK) 应用程序示例。它设置了一个"协调器"智能体，根据定义的指令将用户请求路由到专门的子智能体（"Booker"用于预订，"Info"用于一般信息）。然后子智能体使用特定工具模拟处理请求，展示了智能体系统中的基本委托模式。

```python
## Copyright (c) 2025 Marco Fago
#
## This code is licensed under the MIT License.
## See the LICENSE file in the repository for the full license text.

import uuid
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types
from google.adk.events import Event

## --- Define Tool Functions ---
## These functions simulate the actions of the specialist agents.
def booking_handler(request: str) -> str:
   """
   Handles booking requests for flights and hotels.
   Args:
       request: The user's request for a booking.
   Returns:
       A confirmation message that the booking was handled.
   """
   print("-------------------------- Booking Handler Called ----------------------------")
   return f"Booking action for '{request}' has been simulated."

def info_handler(request: str) -> str:
   """
   Handles general information requests.
   Args:
       request: The user's question.
   Returns:
       A message indicating the information request was handled.
   """
   print("-------------------------- Info Handler Called ----------------------------")
   return f"Information request for '{request}'. Result: Simulated information retrieval."

def unclear_handler(request: str) -> str:
   """Handles requests that couldn't be delegated."""
   return f"Coordinator could not delegate request: '{request}'. Please clarify."

## --- Create Tools from Functions ---
booking_tool = FunctionTool(booking_handler)
info_tool = FunctionTool(info_handler)

## Define specialized sub-agents equipped with their respective tools
booking_agent = Agent(
   name="Booker",
   model="gemini-2.0-flash",
   description="A specialized agent that handles all flight \
           and hotel booking requests by calling the booking tool.",
   tools=[booking_tool]
)

info_agent = Agent(
   name="Info",
   model="gemini-2.0-flash",
   description="A specialized agent that provides general information \
      and answers user questions by calling the info tool.",
   tools=[info_tool]
)

## Define the parent agent with explicit delegation instructions
coordinator = Agent(
   name="Coordinator",
   model="gemini-2.0-flash",
   instruction=(
       "You are the main coordinator. Your only task is to analyze \
       incoming user requests "
       "and delegate them to the appropriate specialist agent. \
        Do not try to answer the user directly.\n"
       "- For any requests related to booking flights or hotels, \
         delegate to the 'Booker' agent.\n"
       "- For all other general information questions, delegate to the 'Info' agent."
   ),
   description="A coordinator that routes user requests to the \
     correct specialist agent.",
   # The presence of sub_agents enables LLM-driven delegation (Auto-Flow) by default.
   sub_agents=[booking_agent, info_agent]
)

## --- Execution Logic ---
async def run_coordinator(runner: InMemoryRunner, request: str):
   """Runs the coordinator agent with a given request and delegates."""
   print(f"\n--- Running Coordinator with request: '{request}' ---")
   final_result = ""
   try:
       user_id = "user_123"
       session_id = str(uuid.uuid4())
       await runner.session_service.create_session(
           app_name=runner.app_name, user_id=user_id, session_id=session_id
       )
       for event in runner.run(
           user_id=user_id,
           session_id=session_id,
           new_message=types.Content(
               role='user',
               parts=[types.Part(text=request)]
           ),
       ):
           if event.is_final_response() and event.content:
               # Try to get text directly from event.content
               # to avoid iterating parts
               if hasattr(event.content, 'text') and event.content.text:
                   final_result = event.content.text
               elif event.content.parts:
                   # Fallback: Iterate through parts and extract text (might trigger warning)
                   text_parts = [part.text for part in event.content.parts if part.text]
                   final_result = "".join(text_parts)
               # Assuming the loop should break after the final response
               break
       print(f"Coordinator Final Response: {final_result}")
       return final_result
   except Exception as e:
       print(f"An error occurred while processing your request: {e}")
       return f"An error occurred while processing your request: {e}"

async def main():
   """Main function to run the ADK example."""
   print("--- Google ADK Routing Example (ADK Auto-Flow Style) ---")
   print("Note: This requires Google ADK installed and authenticated.")
   runner = InMemoryRunner(coordinator)
   # Example Usage
   result_a = await run_coordinator(runner, "Book me a hotel in Paris.")
   print(f"Final Output A: {result_a}")
   result_b = await run_coordinator(runner, "What is the highest mountain in the world?")
   print(f"Final Output B: {result_b}")
   result_c = await run_coordinator(runner, "Tell me a random fact.") # Should go to Info
   print(f"Final Output C: {result_c}")
   result_d = await run_coordinator(runner, "Find flights to Tokyo next month.") # Should go to Booker
   print(f"Final Output D: {result_d}")

if __name__ == "__main__":
   import nest_asyncio
   nest_asyncio.apply()
   await main()
```

This script consists of a main Coordinator agent and two specialized sub\_agents: Booker and Info. Each specialized agent is equipped with a FunctionTool that wraps a Python function simulating an action. The booking\_handler function simulates handling flight and hotel bookings, while the info\_handler function simulates retrieving general information. The unclear\_handler is included as a fallback for requests the coordinator cannot delegate, although the current coordinator logic doesn't explicitly use it for delegation failure in the main run\_coordinator function. 

此脚本由一个主协调器智能体和两个专门的子智能体组成：Booker 和 Info。每个专门的智能体都配备了一个 FunctionTool，它包装了一个模拟操作的 Python 函数。booking_handler 函数模拟处理航班和酒店预订，而 info_handler 函数模拟检索一般信息。unclear_handler 作为协调器无法委托的请求的后备包含在内，尽管当前协调器逻辑在主 run_coordinator 函数中没有明确使用它进行委托失败处理。

The Coordinator agent's primary role, as defined in its instruction, is to analyze incoming user messages and delegate them to either the Booker or Info agent. This delegation is handled automatically by the ADK's Auto-Flow mechanism because the Coordinator has sub\_agents defined. The run\_coordinator function sets up an InMemoryRunner, creates a user and session ID, and then uses the runner to process the user's request through the coordinator agent. The runner.run method processes the request and yields events, and the code extracts the final response text from the event.content. 

协调器智能体的主要角色，如其指令中所定义的，是分析传入的用户消息并将它们委托给 Booker 或 Info 智能体。这种委托由 ADK 的自动流机制自动处理，因为协调器定义了 sub_agents。run_coordinator 函数设置了一个 InMemoryRunner，创建一个用户和会话 ID，然后使用运行器通过协调器智能体处理用户的请求。runner.run 方法处理请求并产生事件，代码从 event.content 中提取最终响应文本。

The main function demonstrates the system's usage by running the coordinator with different requests, showcasing how it delegates booking requests to the Booker and information requests to the Info agent.

main 函数通过使用不同请求运行协调器来演示系统的用法，展示了它如何将预订请求委托给 Booker，将信息请求委托给 Info 智能体。

## At a Glance

## 速览

**What**: Agentic systems must often respond to a wide variety of inputs and situations that cannot be handled by a single, linear process. A simple sequential workflow lacks the ability to make decisions based on context. Without a mechanism to choose the correct tool or sub-process for a specific task, the system remains rigid and non-adaptive. This limitation makes it difficult to build sophisticated applications that can manage the complexity and variability of real-world user requests.

**问题背景：** 智能体系统必须经常响应各种各样的输入和情况，这些无法由单一的线性流程处理。简单的顺序工作流缺乏基于上下文做出决策的能力。没有为特定任务选择正确工具或子流程的机制，系统仍然是僵化和非自适应的。这种限制使得难以构建能够管理现实世界用户请求的复杂性和可变性的复杂应用程序。

**Why:** The Routing pattern provides a standardized solution by introducing conditional logic into an agent's operational framework. It enables the system to first analyze an incoming query to determine its intent or nature. Based on this analysis, the agent dynamically directs the flow of control to the most appropriate specialized tool, function, or sub-agent. This decision can be driven by various methods, including prompting LLMs, applying predefined rules, or using embedding-based semantic similarity. Ultimately, routing transforms a static, predetermined execution path into a flexible and context-aware workflow capable of selecting the best possible action.

**解决方案：** 路由模式通过将条件逻辑引入智能体的操作框架提供了标准化解决方案。它使系统能够首先分析传入查询以确定其意图或性质。基于此分析，智能体动态地将控制流定向到最合适的专门工具、函数或子智能体。这个决策可以由各种方法驱动，包括提示 LLM、应用预定义规则或使用基于嵌入的语义相似性。最终，路由将静态的预定执行路径转变为能够选择最佳可能操作的灵活和上下文感知工作流。

**Rule of Thumb:** Use the Routing pattern when an agent must decide between multiple distinct workflows, tools, or sub-agents based on the user's input or the current state. It is essential for applications that need to triage or classify incoming requests to handle different types of tasks, such as a customer support bot distinguishing between sales inquiries, technical support, and account management questions.

**实践建议：** 当智能体必须根据用户输入或当前状态在多个不同的工作流、工具或子智能体之间做出决策时，使用路由模式。它对于需要对传入请求进行分类以处理不同类型任务的应用程序至关重要，例如客户支持机器人区分销售查询、技术支持和帐户管理问题。

#### **Visual Summary:**

#### **可视化摘要：**

![][image1]  
Fig.1: Router pattern, using an LLM as a Router

图 1：路由模式，使用 LLM 作为路由器

## Key Takeaways

## 关键要点

* Routing enables agents to make dynamic decisions about the next step in a workflow based on conditions.  
* It allows agents to handle diverse inputs and adapt their behavior, moving beyond linear execution.  
* Routing logic can be implemented using LLMs, rule-based systems, or embedding similarity.  
* Frameworks like LangGraph and Google ADK provide structured ways to define and manage routing within agent workflows, albeit with different architectural approaches.

* 路由使智能体能够根据条件动态决定工作流中的下一步。
* 它允许智能体处理各种输入并调整其行为，超越线性执行。
* 路由逻辑可以使用 LLM、基于规则的系统或嵌入相似性实现。
* 像 LangGraph 和 Google ADK 这样的框架提供了在智能体工作流中定义和管理路由的结构化方式，尽管采用不同的架构方法。

## Conclusion

## 结论

The Routing pattern is a critical step in building truly dynamic and responsive agentic systems. By implementing routing, we move beyond simple, linear execution flows and empower our agents to make intelligent decisions about how to process information, respond to user input, and utilize available tools or sub-agents.

路由模式是构建真正动态响应式智能体系统的关键步骤。通过实现路由，我们超越了简单的线性执行流，使智能体能够智能地决策如何处理信息、响应用户输入以及利用可用工具或子智能体。

We've seen how routing can be applied in various domains, from customer service chatbots to complex data processing pipelines. The ability to analyze input and conditionally direct the workflow is fundamental to creating agents that can handle the inherent variability of real-world tasks.

我们已经看到路由如何应用于各个领域，从客户服务聊天机器人到复杂的数据处理管道。分析输入并有条件地指导工作流的能力是创建能够处理现实世界任务固有可变性的智能体的基础。

The code examples using LangChain and Google ADK demonstrate two different, yet effective, approaches to implementing routing. LangGraph's graph-based structure provides a visual and explicit way to define states and transitions, making it ideal for complex, multi-step workflows with intricate routing logic. Google ADK, on the other hand, often focuses on defining distinct capabilities (Tools) and relies on the framework's ability to route user requests to the appropriate tool handler, which can be simpler for agents with a well-defined set of discrete actions.

使用 LangChain 和 Google ADK 的代码示例展示了实现路由的两种不同但有效的方法。LangGraph 基于图的结构提供了定义状态和转换的可视化和显式方式，使其成为具有复杂路由逻辑的复杂多步工作流的理想选择。另一方面，Google ADK 通常专注于定义不同的能力（工具）并依赖框架将用户请求路由到适当的工具处理程序的能力，这对于具有明确定义的离散操作集的智能体来说可能更简单。

Mastering the Routing pattern is essential for building agents that can intelligently navigate different scenarios and provide tailored responses or actions based on context. It's a key component in creating versatile and robust agentic applications.

掌握路由模式对于构建能够智能地导航不同场景并根据上下文提供定制响应或操作的智能体至关重要。它是创建多功能和健壮智能体应用程序的关键组件。

## References

## 参考文献

1. LangGraph Documentation: [https://www.langchain.com/](https://www.langchain.com/)
2. Google Agent Developer Kit Documentation: [https://google.github.io/adk-docs/](https://google.github.io/adk-docs/)

[image1]: ../images/chapter-2/image1.png
