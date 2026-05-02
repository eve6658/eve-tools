# Chapter 3: Parallelization

# 第 3 章：并行化

## Parallelization Pattern Overview

## 并行化模式概述

In the previous chapters, we've explored Prompt Chaining for sequential workflows and Routing for dynamic decision-making and transitions between different paths. While these patterns are essential, many complex agentic tasks involve multiple sub-tasks that can be executed *simultaneously* rather than one after another. This is where the **Parallelization** pattern becomes crucial.

在前面的章节中，我们探讨了用于顺序工作流的提示词链，以及用于动态决策和不同路径间转换的路由。虽然这些模式不可或缺，但许多复杂的智能体任务涉及多个可*同时*执行而非顺序执行的子任务。这正是**并行化**模式的用武之地。

Parallelization involves executing multiple components, such as LLM calls, tool usages, or even entire sub-agents, concurrently (see Fig.1). Instead of waiting for one step to complete before starting the next, parallel execution allows independent tasks to run at the same time, significantly reducing the overall execution time for tasks that can be broken down into independent parts.

并行化是指并发执行多个组件，包括LLM调用、工具使用乃至整个子智能体（见图1）。不同于顺序等待每个步骤完成后再开始下一步，并行执行允许独立任务同时运行，从而显著缩短可分解为独立部分的任务的总执行时间。

Consider an agent designed to research a topic and summarize its findings. A sequential approach might:

设想一个旨在研究某个主题并总结发现的智能体。顺序方法可能是这样的：

1. Search for Source A.  
2. Summarize Source A.  
3. Search for Source B.  
4. Summarize Source B.  
5. Synthesize a final answer from summaries A and B.

1. 搜索来源 A
2. 总结来源 A
3. 搜索来源 B
4. 总结来源 B
5. 基于摘要 A 和 B 合成最终答案

A parallel approach could instead:

而并行方法则可改为：

1. Search for Source A *and* Search for Source B simultaneously.  
2. Once both searches are complete, Summarize Source A *and* Summarize Source B simultaneously.  
3. Synthesize a final answer from summaries A and B (this step is typically sequential, waiting for the parallel steps to finish).

1. *同时*搜索来源 A 和来源 B
2. 两个搜索完成后，*同时*总结来源 A 和来源 B
3. 基于摘要 A 和 B 合成最终答案（此步骤通常为顺序执行，需等待并行步骤完成）

The core idea is to identify parts of the workflow that do not depend on the output of other parts and execute them in parallel. This is particularly effective when dealing with external services (like APIs or databases) that have latency, as you can issue multiple requests concurrently.

核心思想是识别工作流中不依赖其他部分输出的环节并将它们并行执行。这在处理具有延迟的外部服务（如API或数据库）时尤其有效，因为您可以同时发出多个请求。

Implementing parallelization often requires frameworks that support asynchronous execution or multi-threading/multi-processing. Modern agentic frameworks are designed with asynchronous operations in mind, allowing you to easily define steps that can run in parallel.

实现并行化通常需要支持异步执行或多线程/多进程的框架。现代智能体框架在设计时已充分考虑异步操作，让您能够轻松定义可并行运行的步骤。

![][image1]

Fig.1. Example of parallelization with sub-agents

图 1. 带有子智能体的并行化示例

Frameworks like LangChain, LangGraph, and Google ADK provide mechanisms for parallel execution. In LangChain Expression Language (LCEL), you can achieve parallel execution by combining runnable objects using operators like | (for sequential) and by structuring your chains or graphs to have branches that execute concurrently. LangGraph, with its graph structure, allows you to define multiple nodes that can be executed from a single state transition, effectively enabling parallel branches in the workflow. Google ADK provides robust, native mechanisms to facilitate and manage the parallel execution of agents, significantly enhancing the efficiency and scalability of complex, multi-agent systems. This inherent capability within the ADK framework allows developers to design and implement solutions where multiple agents can operate concurrently, rather than sequentially.

像LangChain、LangGraph和Google ADK这样的框架提供了并行执行机制。在LangChain表达式语言（LCEL）中，您可以通过运算符（如 | 用于顺序）组合可运行对象，并通过构建支持分支并发执行的链或图来实现并行执行。LangGraph凭借其图结构，允许定义可从单个状态转换执行的多个节点，从而在工作流中启用并行分支。Google ADK提供了强大的原生机制来促进和管理智能体的并行执行，显著提升了复杂多智能体系统的效率和可扩展性。ADK框架的这一固有能力让开发人员能够设计多个智能体并发而非顺序操作的解决方案。

The Parallelization pattern is vital for improving the efficiency and responsiveness of agentic systems, especially when dealing with tasks that involve multiple independent lookups, computations, or interactions with external services. It's a key technique for optimizing the performance of complex agent workflows.

并行化模式对于提升智能体系统的效率和响应能力至关重要，特别是在处理涉及多个独立查询、计算或与外部服务交互的任务时。它是优化复杂智能体工作流性能的关键技术。

## Practical Applications & Use Cases

## 实际应用与用例

Parallelization is a powerful pattern for optimizing agent performance across various applications:

并行化是优化智能体性能的强大模式，适用于多种应用场景：

1. Information Gathering and Research:
Collecting information from multiple sources simultaneously is a classic use case.

1. 信息收集与研究：
同时从多个来源收集信息是经典用例。

* **Use Case:** An agent researching a company.  
  * **Parallel Tasks:** Search news articles, pull stock data, check social media mentions, and query a company database, all at the same time.  
  * **Benefit:** Gathers a comprehensive view much faster than sequential lookups.

* **用例：** 公司调研智能体
  * **并行任务：** 同时搜索新闻文章、获取股票数据、监控社交媒体提及和查询公司数据库
  * **优势：** 相比顺序查询能更快获得全面视图

2. Data Processing and Analysis:
Applying different analysis techniques or processing different data segments concurrently.

2. 数据处理与分析：
对数据的不同部分进行并发处理，或同时应用不同的分析技术

* **Use Case:** An agent analyzing customer feedback.  
  * **Parallel Tasks:** Run sentiment analysis, extract keywords, categorize feedback, and identify urgent issues simultaneously across a batch of feedback entries.  
  * **Benefit:** Provides a multi-faceted analysis quickly.

* **用例：** 客户反馈分析智能体
  * **并行任务：** 对一批反馈条目同时执行情感分析、关键词提取、反馈分类和紧急问题识别
  * **优势：** 快速提供多维度分析结果

3. Multi-API or Tool Interaction:
Calling multiple independent APIs or tools to gather different types of information or perform different actions.

3. 多 API 或工具交互：
调用多个独立的 API 或工具以获取不同类型信息或执行不同操作

* **Use Case:** A travel planning agent.  
  * **Parallel Tasks:** Check flight prices, search for hotel availability, look up local events, and find restaurant recommendations concurrently.  
  * **Benefit:** Presents a complete travel plan faster.

* **用例：** 旅行规划智能体
  * **并行任务：** 同时查询航班价格、酒店可用性、当地活动和餐厅推荐
  * **优势：** 更快呈现完整的旅行方案

4. Content Generation with Multiple Components:
Generating different parts of a complex piece of content in parallel.

4. 多组件内容生成：
并行生成复杂内容的不同组成部分

* **Use Case:** An agent creating a marketing email.  
  * **Parallel Tasks:** Generate a subject line, draft the email body, find a relevant image, and create a call-to-action button text simultaneously.  
  * **Benefit:** Assembles the final email more efficiently.

* **用例：** 营销邮件创建智能体
  * **并行任务：** 同时生成邮件主题、起草正文内容、查找相关图片和创建行动号召按钮文本
  * **优势：** 更高效地组装最终邮件

5. Validation and Verification:
Performing multiple independent checks or validations concurrently.

5. 验证与核实：
并发执行多个独立检查或验证操作

* **Use Case:** An agent verifying user input.  
  * **Parallel Tasks:** Check email format, validate phone number, verify address against a database, and check for profanity simultaneously.  
  * **Benefit:** Provides faster feedback on input validity.

* **用例：** 用户输入验证智能体
  * **并行任务：** 同时验证邮箱格式、手机号码、地址信息数据库匹配和不当内容检测
  * **优势：** 更快提供输入有效性反馈

6. Multi-Modal Processing:
Processing different modalities (text, image, audio) of the same input concurrently.

6. 多模态处理：
并发处理同一输入的不同模态（文本、图像、音频）

* **Use Case:** An agent analyzing a social media post with text and an image.  
  * **Parallel Tasks:** Analyze the text for sentiment and keywords *and* analyze the image for objects and scene description simultaneously.  
  * **Benefit:** Integrates insights from different modalities more quickly.

* **用例：** 包含文本和图像的社交媒体帖子分析智能体
  * **并行任务：** 同时分析文本情感与关键词*并*识别图像中的对象和场景描述
  * **优势：** 更快速整合来自不同模态的洞察

7. A/B Testing or Multiple Options Generation:
Generating multiple variations of a response or output in parallel to select the best one.

7. A/B 测试或多选项生成：
并行生成多个响应或输出变体以选择最佳方案

* **Use Case:** An agent generating different creative text options.  
  * **Parallel Tasks:** Generate three different headlines for an article simultaneously using slightly different prompts or models.  
  * **Benefit:** Allows for quick comparison and selection of the best option.

* **用例：** 创意文本生成智能体
  * **并行任务：** 使用略有不同的提示或模型同时为文章生成三个不同标题
  * **优势：** 便于快速比较并选择最佳选项

Parallelization is a fundamental optimization technique in agentic design, allowing developers to build more performant and responsive applications by leveraging concurrent execution for independent tasks.

并行化是智能体设计中的基础优化技术，使开发人员能够通过利用独立任务的并发执行来构建更高性能和响应更快的应用程序。

## Hands-On Code Example (LangChain)

## 实操代码示例（LangChain）

Parallel execution within the LangChain framework is facilitated by the LangChain Expression Language (LCEL). The primary method involves structuring multiple runnable components within a dictionary or list construct. When this collection is passed as input to a subsequent component in the chain, the LCEL runtime executes the contained runnables concurrently.

LangChain 框架中的并行执行由 LangChain 表达式语言（LCEL）实现。主要方法是在字典或列表结构中组织多个可运行组件。当该集合作为输入传递给链中的后续组件时，LCEL 运行时会并发执行其中包含的可运行对象。

In the context of LangGraph, this principle is applied to the graph's topology. Parallel workflows are defined by architecting the graph such that multiple nodes, lacking direct sequential dependencies, can be initiated from a single common node. These parallel pathways execute independently before their results can be aggregated at a subsequent convergence point in the graph.

在 LangGraph 中，这一原理应用于图的拓扑结构。并行工作流通过设计图结构来定义，使得多个无直接顺序依赖关系的节点可从单个公共节点启动。这些并行路径独立执行，其结果可在图中的后续汇聚点进行聚合。

The following implementation demonstrates a parallel processing workflow constructed with the LangChain framework. This workflow is designed to execute two independent operations concurrently in response to a single user query. These parallel processes are instantiated as distinct chains or functions, and their respective outputs are subsequently aggregated into a unified result.

以下实现展示了使用 LangChain 框架构建的并行处理工作流。该工作流设计用于响应单个用户查询并发执行多个独立操作。这些并行过程被实例化为不同的链或函数，各自的输出随后被聚合成统一结果。

The prerequisites for this implementation include the installation of the requisite Python packages, such as langchain, langchain-community, and a model provider library like langchain-openai. Furthermore, a valid API key for the chosen language model must be configured in the local environment for authentication.

此实现的先决条件包括安装必要的 Python 包，如 langchain、langchain-community 以及模型提供商库（如 langchain-openai）。此外，还需在本地环境中配置所选语言模型的有效 API 密钥以完成身份验证。

```python
import os
import asyncio
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableParallel, RunnablePassthrough

## --- Configuration ---
## Ensure your API key environment variable is set (e.g., OPENAI_API_KEY)
try:
   llm: Optional[ChatOpenAI] = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
except Exception as e:
   print(f"Error initializing language model: {e}")
   llm = None

## --- Define Independent Chains ---
## These three chains represent distinct tasks that can be executed in parallel.
summarize_chain: Runnable = (
   ChatPromptTemplate.from_messages([
       ("system", "Summarize the following topic concisely:"),
       ("user", "{topic}")
   ])
   | llm
   | StrOutputParser()
)

questions_chain: Runnable = (
   ChatPromptTemplate.from_messages([
       ("system", "Generate three interesting questions about the following topic:"),
       ("user", "{topic}")
   ])
   | llm
   | StrOutputParser()
)

terms_chain: Runnable = (
   ChatPromptTemplate.from_messages([
       ("system", "Identify 5-10 key terms from the following topic, separated by commas:"),
       ("user", "{topic}")
   ])
   | llm
   | StrOutputParser()
)

## --- Build the Parallel + Synthesis Chain ---
## 1. Define the block of tasks to run in parallel. The results of these,
##    along with the original topic, will be fed into the next step.
map_chain = RunnableParallel(
   {
       "summary": summarize_chain,
       "questions": questions_chain,
       "key_terms": terms_chain,
       "topic": RunnablePassthrough(),  # Pass the original topic through
   }
)

## 2. Define the final synthesis prompt which will combine the parallel results.
synthesis_prompt = ChatPromptTemplate.from_messages([
   ("system", """Based on the following information:
   Summary: {summary}
   Related Questions: {questions}
   Key Terms: {key_terms}
   Synthesize a comprehensive answer."""),
   ("user", "Original topic: {topic}")
])

## 3. Construct the full chain by piping the parallel results directly
##    into the synthesis prompt, followed by the LLM and output parser.
full_parallel_chain = map_chain | synthesis_prompt | llm | StrOutputParser()

## --- Run the Chain ---
async def run_parallel_example(topic: str) -> None:
   """
   Asynchronously invokes the parallel processing chain with a specific topic
   and prints the synthesized result.
   Args:
       topic: The input topic to be processed by the LangChain chains.
   """
   if not llm:
       print("LLM not initialized. Cannot run example.")
       return

   print(f"\n--- Running Parallel LangChain Example for Topic: '{topic}' ---")
   try:
       # The input to `ainvoke` is the single 'topic' string,
       # then passed to each runnable in the `map_chain`.
       response = await full_parallel_chain.ainvoke(topic)
       print("\n--- Final Response ---")
       print(response)
   except Exception as e:
       print(f"\nAn error occurred during chain execution: {e}")

if __name__ == "__main__":
   test_topic = "The history of space exploration"
   # In Python 3.7+, asyncio.run is the standard way to run an async function.
   asyncio.run(run_parallel_example(test_topic))
```

The provided Python code implements a LangChain application designed for processing a given topic efficiently by leveraging parallel execution. Note that asyncio provides concurrency, not parallelism. It achieves this on a single thread by using an event loop that intelligently switches between tasks when one is idle (e.g., waiting for a network request). This creates the effect of multiple tasks progressing at once, but the code itself is still being executed by only one thread, constrained by Python's Global Interpreter Lock (GIL). 

上述 Python 代码实现了一个 LangChain 应用程序，旨在通过并行执行高效处理给定主题。请注意，asyncio 提供的是并发性而非真正的并行性。它通过事件循环在单线程上实现这一点，在任务空闲时（如等待网络请求）智能地在任务间切换。这创造了多个任务同时进行的效果，但代码实际上仍由单个线程执行，受 Python 全局解释器锁（GIL）限制。

The code begins by importing essential modules from langchain_openai and langchain_core, including components for language models, prompts, output parsing, and runnable structures. The code attempts to initialize a ChatOpenAI instance, specifically using the "gpt-4o-mini" model, with a specified temperature for controlling creativity. A try-except block is used for robustness during the language model initialization. Three independent LangChain "chains" are then defined, each designed to perform a distinct task on the input topic. The first chain is for summarizing the topic concisely, using a system message and a user message containing the topic placeholder. The second chain is configured to generate three interesting questions related to the topic. The third chain is set up to identify between 5 and 10 key terms from the input topic, requesting them to be comma-separated. Each of these independent chains consists of a ChatPromptTemplate tailored to its specific task, followed by the initialized language model and a StrOutputParser to format the output as a string. 

代码首先从 langchain_openai 和 langchain_core 导入必要模块，包括语言模型、提示模板、输出解析器和可运行结构组件。代码尝试初始化 ChatOpenAI 实例，使用"gpt-4o-mini"模型并设置温度参数以控制创造性。语言模型初始化采用 try-except 块以确保健壮性。随后定义三个独立的 LangChain"链"，每个链设计用于对输入主题执行不同任务：第一个链负责简洁总结主题，第二个链生成与主题相关的三个有趣问题，第三个链从输入主题中识别 5-10 个关键术语并以逗号分隔。每个独立链都由针对特定任务定制的 ChatPromptTemplate、初始化的语言模型和用于字符串格式输出的 StrOutputParser 组成。

A RunnableParallel block is then constructed to bundle these three chains, allowing them to execute simultaneously. This parallel runnable also includes a RunnablePassthrough to ensure the original input topic is available for subsequent steps. A separate ChatPromptTemplate is defined for the final synthesis step, taking the summary, questions, key terms, and the original topic as input to generate a comprehensive answer. The full end-to-end processing chain, named full_parallel_chain, is created by sequencing the map_chain (the parallel block) into the synthesis prompt, followed by the language model and the output parser. An asynchronous function run_parallel_example is provided to demonstrate how to invoke this full_parallel_chain. This function takes the topic as input and uses invoke to run the asynchronous chain. Finally, the standard Python if __name__ == "__main__": block shows how to execute the run_parallel_example with a sample topic, in this case, "The history of space exploration", using asyncio.run to manage the asynchronous execution.

然后构建 RunnableParallel 块来捆绑这三个链以实现同时执行。此并行可运行对象还包含 RunnablePassthrough 以确保原始输入主题可用于后续步骤。为最终综合步骤定义了单独的 ChatPromptTemplate，接收摘要、问题、关键术语和原始主题作为输入以生成全面答案。完整的端到端处理链（full_parallel_chain）通过将 map_chain（并行块）连接到综合提示模板，再接入语言模型和输出解析器来创建。提供的异步函数 run_parallel_example 演示了如何调用此完整并行链，该函数接收主题作为输入并使用 invoke 运行异步链。最后，标准 Python if __name__ == "__main__": 块展示了如何使用示例主题"太空探索的历史"执行 run_parallel_example，通过 asyncio.run 管理异步执行。

In essence, this code sets up a workflow where multiple LLM calls (for summarizing, questions, and terms) happen at the same time for a given topic, and their results are then combined by a final LLM call. This showcases the core idea of parallelization in an agentic workflow using LangChain.

本质上，此代码建立了一个工作流，对给定主题同时执行多个 LLM 调用（用于总结、生成问题和提取术语），最终通过另一个 LLM 调用整合结果。这展示了在智能体工作流中使用 LangChain 实现并行化的核心思想。

## Hands-On Code Example (Google ADK)

## 实操代码示例（Google ADK）

Okay, let's now turn our attention to a concrete example illustrating these concepts within the Google ADK framework. We'll examine how the ADK primitives, such as ParallelAgent and SequentialAgent, can be applied to build an agent flow that leverages concurrent execution for improved efficiency.

现在让我们关注 Google ADK 框架中说明这些概念的具体示例。我们将探讨如何应用 ADK 原语（如 ParallelAgent 和 SequentialAgent）来构建利用并发执行提升效率的智能体流程。

```python
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search

GEMINI_MODEL="gemini-2.0-flash"

## --- 1. Define Researcher Sub-Agents (to run in parallel) ---
## Researcher 1: Renewable Energy
researcher_agent_1 = LlmAgent(
    name="RenewableEnergyResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in energy. Research the latest advancements in 'renewable energy sources'. Use the Google Search tool provided. Summarize your key findings concisely (1-2 sentences). Output *only* the summary. """,
    description="Researches renewable energy sources.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="renewable_energy_result"
)

## Researcher 2: Electric Vehicles
researcher_agent_2 = LlmAgent(
    name="EVResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in transportation. Research the latest developments in 'electric vehicle technology'. Use the Google Search tool provided. Summarize your key findings concisely (1-2 sentences). Output *only* the summary. """,
    description="Researches electric vehicle technology.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="ev_technology_result"
)

## Researcher 3: Carbon Capture
researcher_agent_3 = LlmAgent(
    name="CarbonCaptureResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in climate solutions. Research the current state of 'carbon capture methods'. Use the Google Search tool provided. Summarize your key findings concisely (1-2 sentences). Output *only* the summary. """,
    description="Researches carbon capture methods.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="carbon_capture_result"
)

## --- 2. Create the ParallelAgent (Runs researchers concurrently) ---
## This agent orchestrates the concurrent execution of the researchers.
## It finishes once all researchers have completed and stored their results in state.
parallel_research_agent = ParallelAgent(
    name="ParallelWebResearchAgent",
    sub_agents=[researcher_agent_1, researcher_agent_2, researcher_agent_3],
    description="Runs multiple research agents in parallel to gather information."
)

## --- 3. Define the Merger Agent (Runs *after* the parallel agents) ---
## This agent takes the results stored in the session state by the parallel agents
## and synthesizes them into a single, structured response with attributions.
merger_agent = LlmAgent(
    name="SynthesisAgent",
    model=GEMINI_MODEL,  # Or potentially a more powerful model if needed for synthesis
    instruction="""You are an AI Assistant responsible for combining research findings into a structured report. Your primary task is to synthesize the following research summaries, clearly attributing findings to their source areas. Structure your response using headings for each topic. Ensure the report is coherent and integrates the key points smoothly. **Crucially: Your entire response MUST be grounded *exclusively* on the information provided in the 'Input Summaries' below. Do NOT add any external knowledge, facts, or details not present in these specific summaries.** **Input Summaries:** *   **Renewable Energy:**     {renewable_energy_result} *   **Electric Vehicles:**     {ev_technology_result} *   **Carbon Capture:**     {carbon_capture_result} **Output Format:** ## Summary of Recent Sustainable Technology Advancements ### Renewable Energy Findings (Based on RenewableEnergyResearcher's findings) [Synthesize and elaborate *only* on the renewable energy input summary provided above.] ### Electric Vehicle Findings (Based on EVResearcher's findings) [Synthesize and elaborate *only* on the EV input summary provided above.] ### Carbon Capture Findings (Based on CarbonCaptureResearcher's findings) [Synthesize and elaborate *only* on the carbon capture input summary provided above.] ### Overall Conclusion [Provide a brief (1-2 sentence) concluding statement that connects *only* the findings presented above.] Output *only* the structured report following this format. Do not include introductory or concluding phrases outside this structure, and strictly adhere to using only the provided input summary content. """,
    description="Combines research findings from parallel agents into a structured, cited report, strictly grounded on provided inputs.",
    # No tools needed for merging
    # No output_key needed here, as its direct response is the final output of the sequence
)

## --- 4. Create the SequentialAgent (Orchestrates the overall flow) ---
## This is the main agent that will be run. It first executes the ParallelAgent
## to populate the state, and then executes the MergerAgent to produce the final output.
sequential_pipeline_agent = SequentialAgent(
    name="ResearchAndSynthesisPipeline",
    # Run parallel research first, then merge
    sub_agents=[parallel_research_agent, merger_agent],
    description="Coordinates parallel research and synthesizes the results."
)

root_agent = sequential_pipeline_agent
```

This code defines a multi-agent system used to research and synthesize information on sustainable technology advancements. It sets up three LlmAgent instances to act as specialized researchers. ResearcherAgent_1 focuses on renewable energy sources, ResearcherAgent_2 researches electric vehicle technology, and ResearcherAgent_3 investigates carbon capture methods. Each researcher agent is configured to use a GEMINI_MODEL and the google_search tool. They are instructed to summarize their findings concisely (1-2 sentences) and store these summaries in the session state using output_key.

此代码定义了一个用于研究和综合可持续技术进展信息的多智能体系统。系统设置了三个 LlmAgent 实例作为专门的研究员：ResearcherAgent_1 专注于可再生能源，ResearcherAgent_2 研究电动汽车技术，ResearcherAgent_3 调查碳捕获方法。每个研究员智能体配置使用 GEMINI_MODEL 和 google_search 工具，被指示用 1-2 句话简洁总结发现，并通过 output_key 将摘要存储在会话状态中。

A ParallelAgent named ParallelWebResearchAgent is then created to run these three researcher agents concurrently. This allows the research to be conducted in parallel, potentially saving time. The ParallelAgent completes its execution once all its sub-agents (the researchers) have finished and populated the state.

随后创建名为 ParallelWebResearchAgent 的 ParallelAgent 来并发运行这三个研究员智能体，实现并行研究以节省时间。当所有子智能体（研究员）完成并填充状态后，ParallelAgent 结束执行。

Next, a MergerAgent (also an LlmAgent) is defined to synthesize the research results. This agent takes the summaries stored in the session state by the parallel researchers as input. Its instruction emphasizes that the output must be strictly based only on the provided input summaries, prohibiting the addition of external knowledge. The MergerAgent is designed to structure the combined findings into a report with headings for each topic and a brief overall conclusion.

接下来定义 MergerAgent（同样是 LlmAgent）来综合研究结果。该智能体以并行研究员存储在会话状态中的摘要作为输入，其指令强调输出必须严格基于提供的输入摘要，禁止添加外部知识。MergerAgent 旨在将组合的发现结构化为带有各主题标题和简短总体结论的报告。

Finally, a SequentialAgent named ResearchAndSynthesisPipeline is created to orchestrate the entire workflow. As the primary controller, this main agent first executes the ParallelAgent to perform the research. Once the ParallelAgent is complete, the SequentialAgent then executes the MergerAgent to synthesize the collected information. The sequential_pipeline_agent is set as the root_agent, representing the entry point for running this multi-agent system. The overall process is designed to efficiently gather information from multiple sources in parallel and then combine it into a single, structured report.

最后创建名为 ResearchAndSynthesisPipeline 的 SequentialAgent 来协调整个工作流。作为主控制器，该主智能体首先执行 ParallelAgent 进行研究，待其完成后执行 MergerAgent 综合收集的信息。sequential_pipeline_agent 被设置为 root_agent，作为运行此多智能体系统的入口点。整个过程旨在高效地从多个来源并行收集信息，并将其整合为单一结构化报告。

## At a Glance

## 速览

**What:** Many agentic workflows involve multiple sub-tasks that must be completed to achieve a final goal. A purely sequential execution, where each task waits for the previous one to finish, is often inefficient and slow. This latency becomes a significant bottleneck when tasks depend on external I/O operations, such as calling different APIs or querying multiple databases. Without a mechanism for concurrent execution, the total processing time is the sum of all individual task durations, hindering the system's overall performance and responsiveness.

**问题背景：** 许多智能体工作流包含多个必须完成才能达成最终目标的子任务。纯顺序执行（每个任务等待前一个完成）通常低效且缓慢。当任务依赖外部 I/O 操作（如调用不同 API 或查询多个数据库）时，这种延迟成为主要瓶颈。若无并发执行机制，总处理时间等于所有单个任务持续时间之和，严重制约系统整体性能和响应能力。

**Why:** The Parallelization pattern provides a standardized solution by enabling the simultaneous execution of independent tasks. It works by identifying components of a workflow, like tool usages or LLM calls, that do not rely on each other's immediate outputs. Agentic frameworks like LangChain and the Google ADK provide built-in constructs to define and manage these concurrent operations. For instance, a main process can invoke several sub-tasks that run in parallel and wait for all of them to complete before proceeding to the next step. By running these independent tasks at the same time rather than one after another, this pattern drastically reduces the total execution time.

**解决方案：** 并行化模式通过启用独立任务的同时执行提供标准化解决方案。该模式通过识别工作流中不依赖彼此即时输出的组件（如工具使用或 LLM 调用）来实现。像 LangChain 和 Google ADK 这样的智能体框架提供内置构造来定义和管理这些并发操作。例如，主进程可调用多个并行运行的子任务，等待所有子任务完成后再继续下一步。通过同时而非顺序执行这些独立任务，该模式显著减少总执行时间。

**Rule of thumb:** Use this pattern when a workflow contains multiple independent operations that can run simultaneously, such as fetching data from several APIs, processing different chunks of data, or generating multiple pieces of content for later synthesis.

**实践建议：** 当工作流包含多个可同时运行的独立操作时使用此模式，例如从多个 API 获取数据、处理不同数据块或生成多个内容片段供后续综合。

**Visual summary**

**可视化摘要**

![][image2]

Fig.2: Parallelization design pattern

图 2：并行化设计模式

## Key Takeaways

## 关键要点

Here are the key takeaways:

以下是本章的核心要点：

* Parallelization is a pattern for executing independent tasks concurrently to improve efficiency.  
* 并行化是一种通过并发执行独立任务来提高效率的模式

* It is particularly useful when tasks involve waiting for external resources, such as API calls.  
* 在涉及等待外部资源（如 API 调用）的任务中特别有效

* The adoption of a concurrent or parallel architecture introduces substantial complexity and cost, impacting key development phases such as design, debugging, and system logging.  
* 采用并发或并行架构会引入显著复杂性和成本，影响设计、调试和系统日志等关键开发环节

* Frameworks like LangChain and Google ADK provide built-in support for defining and managing parallel execution.  
* 像 LangChain 和 Google ADK 这样的框架提供定义和管理并行执行的内置支持

* In LangChain Expression Language (LCEL), RunnableParallel is a key construct for running multiple runnables side-by-side.  
* 在 LangChain 表达式语言（LCEL）中，RunnableParallel 是并行运行多个可运行对象的关键构造

* Google ADK can facilitate parallel execution through LLM-Driven Delegation, where a Coordinator agent's LLM identifies independent sub-tasks and triggers their concurrent handling by specialized sub-agents.  
* Google ADK 可通过 LLM 驱动的委托实现并行执行，协调器智能体的 LLM 识别独立子任务并触发专门子智能体的并发处理

* Parallelization helps reduce overall latency and makes agentic systems more responsive for complex tasks.

* 并行化有助于减少整体延迟，使智能体系统在处理复杂任务时更具响应性

## Conclusion

## 结论

The parallelization pattern is a method for optimizing computational workflows by concurrently executing independent sub-tasks. This approach reduces overall latency, particularly in complex operations that involve multiple model inferences or calls to external services.

并行化模式是通过并发执行独立子任务来优化计算工作流的方法。该模式有效减少整体延迟，在涉及多个模型推理或对外部服务调用的复杂操作中尤为显著。

Frameworks provide distinct mechanisms for implementing this pattern. In LangChain, constructs like RunnableParallel are used to explicitly define and execute multiple processing chains simultaneously. In contrast, frameworks like the Google Agent Developer Kit (ADK) can achieve parallelization through multi-agent delegation, where a primary coordinator model assigns different sub-tasks to specialized agents that can operate concurrently.

不同框架为此模式提供了不同的实现机制。在 LangChain 中，通过 RunnableParallel 等构造显式定义并同时执行多个处理链。而 Google 智能体开发工具包 (ADK) 等框架则通过多智能体委托实现并行化，由主协调器模型将不同子任务分配给可并发操作的专门智能体。

By integrating parallel processing with sequential (chaining) and conditional (routing) control flows, it becomes possible to construct sophisticated, high-performance computational systems capable of efficiently managing diverse and complex tasks.

通过将并行处理与顺序（链式）和条件（路由）控制流相结合，可以构建能够高效管理各类复杂任务的复杂、高性能计算系统。

## References

## 参考文献

Here are some resources for further reading on the Parallelization pattern and related concepts:

以下是有关并行化模式和相关概念的一些进一步阅读资源：

1. LangChain Expression Language (LCEL) Documentation (Parallelism): [https://python.langchain.com/docs/concepts/lcel/](https://python.langchain.com/docs/concepts/lcel/)   
1. LangChain 表达式语言 (LCEL) 文档（并行性）：[https://python.langchain.com/docs/concepts/lcel/](https://python.langchain.com/docs/concepts/lcel/)

2. Google Agent Developer Kit (ADK) Documentation (Multi-Agent Systems): [https://google.github.io/adk-docs/agents/multi-agents/](https://google.github.io/adk-docs/agents/multi-agents/)  
2. Google 智能体开发工具包 (ADK) 文档（多智能体系统）：[https://google.github.io/adk-docs/agents/multi-agents/](https://google.github.io/adk-docs/agents/multi-agents/)

3. Python asyncio Documentation: [https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
3. Python asyncio 文档：[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)

[image1]: ../images/chapter-3/image1.png
[image2]: ../images/chapter-3/image2.png
