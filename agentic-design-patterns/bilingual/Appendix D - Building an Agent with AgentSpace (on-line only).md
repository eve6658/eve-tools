---
layout: bilingual
lang: bilingual
---

# Appendix D - Building an Agent with AgentSpace

# 附录 D - 使用 AgentSpace 构建智能体

## Overview

## 概述

AgentSpace is a platform designed to facilitate an "agent-driven enterprise" by integrating artificial intelligence into daily workflows. At its core, it provides a unified search capability across an organization's entire digital footprint, including documents, emails, and databases. This system utilizes advanced AI models, like Google's Gemini, to comprehend and synthesize information from these varied sources.

AgentSpace 是一个旨在通过将人工智能融入日常工作流程来推动"智能体驱动型企业"发展的平台。其核心能力在于为组织的整个数字资产（包括文档、电子邮件和数据库）提供统一的搜索功能。该系统利用先进的 AI 模型（如 Google 的 Gemini）来理解并整合来自这些多样化来源的信息。

The platform enables the creation and deployment of specialized AI "agents" that can perform complex tasks and automate processes. These agents are not merely chatbots; they can reason, plan, and execute multi-step actions autonomously. For instance, an agent could research a topic, compile a report with citations, and even generate an audio summary.

该平台支持创建和部署专业化的 AI "智能体"，这些智能体执行复杂任务并实现流程自动化。它们不仅是聊天机器人，更具备自主推理、规划和执行多步骤操作的能力。例如，一个智能体可以研究特定主题，编纂带引用的报告，甚至生成音频摘要。

To achieve this, AgentSpace constructs an enterprise knowledge graph, mapping the relationships between people, documents, and data. This allows the AI to understand context and deliver more relevant and personalized results. The platform also includes a no-code interface called Agent Designer for creating custom agents without requiring deep technical expertise.

为了实现这一目标，AgentSpace 构建了企业知识图谱，映射人员、文档和数据之间的关联关系。这使得 AI 能够理解上下文，提供更相关且个性化的结果。平台还包含名为 Agent Designer（智能体设计器）的无代码界面，无需深厚技术专长即可创建自定义智能体。

Furthermore, AgentSpace supports a multi-agent system where different AI agents can communicate and collaborate through an open protocol known as the Agent2Agent (A2A) Protocol. This interoperability allows for more complex and orchestrated workflows. Security is a foundational component, with features like role-based access controls and data encryption to protect sensitive enterprise information. Ultimately, AgentSpace aims to enhance productivity and decision-making by embedding intelligent, autonomous systems directly into an organization's operational fabric.

此外，AgentSpace 支持多智能体系统，不同的 AI 智能体可通过名为 Agent2Agent（A2A）协议的开放协议进行通信与协作。这种互操作性支持更复杂、协调的工作流。安全性是其基础架构的核心组成部分，具备基于角色的访问控制和数据加密等功能，以保护企业敏感信息。最终，AgentSpace 旨在通过将智能自主系统直接嵌入组织运营架构，提升生产力与决策水平。

## How to build an Agent with AgentSpace UI

## 如何使用 AgentSpace UI 构建智能体

Figure 1 illustrates how to access AgentSpace by selecting AI Applications from the Google Cloud Console.

![How to use Google Cloud Console to access AgentSpace](../images/appendix-d/image1.png)

Fig. 1: How to use Google Cloud Console to access AgentSpace

图 1 展示了如何通过 Google Cloud Console 选择 AI Applications 来访问 AgentSpace。

Your agent can be connected to various services, including Calendar, Google Mail, Workday, Jira, Outlook, and Service Now (see Fig. 2).

![Integrate with diverse services, including Google and third-party platforms](../images/appendix-d/image2.png)

Fig. 2: Integrate with diverse services, including Google and third-party platforms.

您的智能体可以连接到多种服务，包括 Calendar、Google Mail、Workday、Jira、Outlook 和 Service Now（见图 2）。

The Agent can then utilize its own prompt, chosen from a gallery of pre-made prompts provided by Google, as illustrated in Fig. 3.

![Google's Gallery of Pre-assembled prompts](../images/appendix-d/image3.png)

Fig. 3: Google's Gallery of Pre-assembled prompts

随后，智能体可以使用自己的提示词，也可以从 Google 提供的预制提示词库中选择，如图 3 所示。

Alternatively, you can create your own prompt as in Fig. 4, which will then be used by your agent.

![Customizing the Agent's Prompt](../images/appendix-d/image4.png)

Fig. 4: Customizing the Agent's Prompt

或者，您可以创建自己的提示词，如图 4 所示，供您的智能体使用。

AgentSpace offers a number of advanced features such as integration with datastores to store your own data, integration with Google Knowledge Graph or with your private Knowledge Graph, Web interface for exposing your agent to the Web, and Analytics to monitor usage, and more (see Fig. 5).

![AgentSpace advanced capabilities](../images/appendix-d/image5.png)

Fig. 5: AgentSpace advanced capabilities

AgentSpace 提供多项高级功能，例如与数据存储集成以存储自有数据、与 Google 知识图谱或私有知识图谱集成、用于向 Web 公开智能体的 Web 界面、使用情况监控分析等（见图 5）。

Upon completion, the AgentSpace chat interface (Fig. 6) will be accessible.

![The AgentSpace User Interface for initiating a chat with your Agent](../images/appendix-d/image6.png)

Fig. 6: The AgentSpace User Interface for initiating a chat with your Agent.

配置完成后，即可访问 AgentSpace 聊天界面（图 6）。

## Conclusion

## 结论

In conclusion, AgentSpace provides a functional framework for developing and deploying AI agents within an organization's existing digital infrastructure. The system's architecture links complex backend processes, such as autonomous reasoning and enterprise knowledge graph mapping, to a graphical user interface for agent construction. Through this interface, users can configure agents by integrating various data services and defining their operational parameters via prompts, resulting in customized, context-aware automated systems.

综上所述，AgentSpace 为在组织现有数字基础设施中开发和部署 AI 智能体提供了实用框架。该系统的架构将复杂的后端流程（如自主推理和企业知识图谱映射）与用于构建智能体的图形用户界面相连接。通过该界面，用户可整合各类数据服务，并通过提示词定义操作参数，从而配置出定制化、情境感知的自动化系统。

This approach abstracts the underlying technical complexity, enabling the construction of specialized multi-agent systems without requiring deep programming expertise. The primary objective is to embed automated analytical and operational capabilities directly into workflows, thereby increasing process efficiency and enhancing data-driven analysis. For practical instruction, hands-on learning modules are available, such as the "Build a Gen AI Agent with Agentspace" lab on Google Cloud Skills Boost, which provides a structured environment for skill acquisition.

这种方法抽象了底层的技术复杂性，使得无需深厚编程知识即可构建专业化的多智能体系统。其主要目标是将自动化分析与操作能力直接嵌入工作流程中，从而提升流程效率、强化数据驱动分析。对于实践指导，现有实践学习模块可供使用，例如 Google Cloud Skills Boost 平台上的"使用 Agentspace 构建 Gen AI 智能体"实验，为技能习得提供了结构化环境。

## References

## 参考文献

1. Create a no-code agent with Agent Designer, [https://cloud.google.com/agentspace/agentspace-enterprise/docs/agent-designer](https://cloud.google.com/agentspace/agentspace-enterprise/docs/agent-designer)

2. Google Cloud Skills Boost, [https://www.cloudskillsboost.google/](https://www.cloudskillsboost.google/)
