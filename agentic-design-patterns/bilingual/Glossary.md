# Glossary

# 术语表

## Fundamental Concepts

## 基础概念

**Prompt:** A prompt is the input, typically in the form of a question, instruction, or statement, that a user provides to an AI model to elicit a response. The quality and structure of the prompt heavily influence the model's output, making prompt engineering a key skill for effectively using AI.

**提示词（Prompt）：** 提示词是用户向 AI 模型提供的输入，通常以问题、指令或陈述形式呈现，旨在激发模型生成相应输出。提示词的质量与结构深度影响模型响应效果，使提示工程成为高效运用 AI 的核心技能。

**Context Window:** The context window is the maximum number of tokens an AI model can process at once, including both the input and its generated output. This fixed size is a critical limitation, as information outside the window is ignored, while larger windows enable more complex conversations and document analysis.

**上下文窗口（Context Window）：** 上下文窗口指 AI 模型单次处理的最大 token 容量，涵盖输入内容与生成输出。此固定尺寸构成关键限制——超出窗口范围的信息将被忽略，而更大窗口则支持更复杂对话交互与文档分析能力。

**In-Context Learning:** In-context learning is an AI's ability to learn a new task from examples provided directly in the prompt, without requiring any retraining. This powerful feature allows a single, general-purpose model to be adapted to countless specific tasks on the fly.

**上下文学习（In-Context Learning）：** 上下文学习是 AI 通过提示中直接嵌入的示例掌握新任务的能力，无需额外训练过程。此强大特性使单一通用模型可即时适配海量特定任务场景。

**Zero-Shot, One-Shot, & Few-Shot Prompting:** These are prompting techniques where a model is given zero, one, or a few examples of a task to guide its response. Providing more examples generally helps the model better understand the user's intent and improves its accuracy for the specific task.

**零样本、单样本与少样本提示（Zero-Shot, One-Shot, & Few-Shot Prompting）：** 此类提示技术通过提供零个、单个或少量任务示例引导模型生成响应。增加示例数量通常能提升模型对用户意图的把握精度，增强特定任务表现。

**Multimodality:** Multimodality is an AI's ability to understand and process information across multiple data types like text, images, and audio. This allows for more versatile and human-like interactions, such as describing an image or answering a spoken question.

**多模态（Multimodality）：** 多模态指 AI 理解并处理跨数据类型信息（如文本、图像、音频）的能力。该特性支持更丰富类人化交互，例如图像描述或语音问答场景。

**Grounding:** Grounding is the process of connecting a model's outputs to verifiable, real-world information sources to ensure factual accuracy and reduce hallucinations. This is often achieved with techniques like RAG to make AI systems more trustworthy.

**基础化（Grounding）：** 基础化是将模型输出关联至可验证真实信息源的过程，旨在确保事实准确性并降低幻觉发生。常通过 RAG 等技术实现，提升 AI 系统可信度。

## Core AI Model Architectures

## 核心 AI 模型架构

**Transformers:** The Transformer is the foundational neural network architecture for most modern LLMs. Its key innovation is the self-attention mechanism, which efficiently processes long sequences of text and captures complex relationships between words.

**Transformer：** Transformer 构成多数现代 LLM 的基石神经网络架构。其核心创新自注意力机制能高效处理长文本序列，精准捕捉词汇间复杂关联。

**Recurrent Neural Network (RNN):** The Recurrent Neural Network is a foundational architecture that preceded the Transformer. RNNs process information sequentially, using loops to maintain a "memory" of previous inputs, which made them suitable for tasks like text and speech processing.

**循环神经网络（Recurrent Neural Network, RNN）：** 循环神经网络是早于 Transformer 的基础架构。RNN 采用序列化信息处理方式，通过循环结构维持对历史输入的"记忆"，曾广泛应用于文本与语音处理任务。

**Mixture of Experts (MoE):** Mixture of Experts is an efficient model architecture where a "router" network dynamically selects a small subset of "expert" networks to handle any given input. This allows models to have a massive number of parameters while keeping computational costs manageable.

**专家混合（Mixture of Experts, MoE）：** 专家混合为高效模型架构，通过"路由"网络动态筛选少量"专家"网络处理特定输入。该设计使模型在保持海量参数规模的同时，有效控制计算开销。

**Diffusion Models:** Diffusion models are generative models that excel at creating high-quality images. They work by adding random noise to data and then training a model to meticulously reverse the process, allowing them to generate novel data from a random starting point.

**扩散模型（Diffusion Models）：** 扩散模型是专精高质量图像生成的生成式模型。其工作原理是通过向数据注入随机噪声，继而训练模型精确逆转该过程，从而实现从随机初始状态生成新颖数据。

**Mamba:** Mamba is a recent AI architecture using a Selective State Space Model (SSM) to process sequences with high efficiency, especially for very long contexts. Its selective mechanism allows it to focus on relevant information while filtering out noise, making it a potential alternative to the Transformer.

**Mamba：** Mamba 是采用选择性状态空间模型（Selective State Space Model, SSM）的新兴 AI 架构，具备超长上下文序列的高效处理能力。其选择性机制可聚焦相关信息同时滤除噪声，被视为 Transformer 的潜在替代方案。

## The LLM Development Lifecycle

## LLM 开发生命周期

The development of a powerful language model follows a distinct sequence. It begins with Pre-training, where a massive base model is built by training it on a vast dataset of general internet text to learn language, reasoning, and world knowledge. Next is Fine-tuning, a specialization phase where the general model is further trained on smaller, task-specific datasets to adapt its capabilities for a particular purpose. The final stage is Alignment, where the specialized model's behavior is adjusted to ensure its outputs are helpful, harmless, and aligned with human values.

强大语言模型的开发遵循明确演进路径。初始阶段为预训练（Pre-training）——通过海量通用互联网文本数据集训练构建大规模基础模型，掌握语言规律、推理能力与世界知识。随后进入微调（Fine-tuning）阶段，通用模型在较小规模任务特定数据集上进一步训练，实现面向特定场景的能力适配。最终阶段为对齐（Alignment），调整专业化模型行为模式，确保输出兼具实用性、安全性且符合人类价值导向。

**Pre-training Techniques:** Pre-training is the initial phase where a model learns general knowledge from vast amounts of data. The top techniques for this involve different objectives for the model to learn from. The most common is Causal Language Modeling (CLM), where the model predicts the next word in a sentence. Another is Masked Language Modeling (MLM), where the model fills in intentionally hidden words in a text. Other important methods include Denoising Objectives, where the model learns to restore a corrupted input to its original state, Contrastive Learning, where it learns to distinguish between similar and dissimilar pieces of data, and Next Sentence Prediction (NSP), where it determines if two sentences logically follow each other.

**预训练技术（Pre-training Techniques）：** 预训练是模型从海量数据中汲取通用知识的奠基阶段。该领域顶尖技术涵盖多样化的学习目标设定。最普遍的是因果语言建模（Causal Language Modeling, CLM），模型通过预测句中下一词汇进行学习。另一主流方法是掩码语言建模（Masked Language Modeling, MLM），模型负责还原文本中被刻意遮蔽的词汇。其他关键方法论包括：去噪目标（Denoising Objectives）——模型学习将受损输入修复至原始状态；对比学习（Contrastive Learning）——模型习得区分相似与相异数据片段的能力；以及下句预测（Next Sentence Prediction, NSP）——模型判断两句间是否存在逻辑连贯性。

**Fine-tuning Techniques:** Fine-tuning is the process of adapting a general pre-trained model to a specific task using a smaller, specialized dataset. The most common approach is Supervised Fine-Tuning (SFT), where the model is trained on labeled examples of correct input-output pairs. A popular variant is Instruction Tuning, which focuses on training the model to better follow user commands. To make this process more efficient, Parameter-Efficient Fine-Tuning (PEFT) methods are used, with top techniques including LoRA (Low-Rank Adaptation), which only updates a small number of parameters, and its memory-optimized version, QLoRA. Another technique, Retrieval-Augmented Generation (RAG), enhances the model by connecting it to an external knowledge source during the fine-tuning or inference stage.

**微调技术（Fine-tuning Techniques）：** 微调是使用专业化小规模数据集将通用预训练模型适配至特定任务的过程。最常用方法为监督微调（Supervised Fine-Tuning, SFT），模型在标注准确的输入输出配对示例上进行训练。指令微调（Instruction Tuning）作为流行变体，重点提升模型遵循用户指令的精准度。为提升过程效率，普遍采用参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）方法，其中代表性技术包括 LoRA（低秩适应）——仅更新少量参数，及其内存优化版本 QLoRA。检索增强生成（Retrieval-Augmented Generation, RAG）作为补充技术，通过在微调或推理阶段连接外部知识源增强模型能力。

**Alignment & Safety Techniques:** Alignment is the process of ensuring an AI model's behavior aligns with human values and expectations, making it helpful and harmless. The most prominent technique is Reinforcement Learning from Human Feedback (RLHF), where a "reward model" trained on human preferences guides the AI's learning process, often using an algorithm like Proximal Policy Optimization (PPO) for stability. Simpler alternatives have emerged, such as Direct Preference Optimization (DPO), which bypasses the need for a separate reward model, and Kahneman-Tversky Optimization (KTO), which simplifies data collection further. To ensure safe deployment, Guardrails are implemented as a final safety layer to filter outputs and block harmful actions in real-time.

**对齐与安全技术（Alignment & Safety Techniques）：** 对齐是确保 AI 模型行为契合人类价值观与期望的过程，使其输出兼具帮助性与安全性。最突出的技术是基于人类反馈的强化学习（Reinforcement Learning from Human Feedback, RLHF），通过基于人类偏好训练的"奖励模型"指导 AI 学习过程，常辅以近端策略优化（Proximal Policy Optimization, PPO）等算法保障训练稳定性。近年涌现的简化替代方案包括直接偏好优化（Direct Preference Optimization, DPO）——规避独立奖励模型需求，以及卡尼曼-特沃斯基优化（Kahneman-Tversky Optimization, KTO）——进一步简化数据收集流程。为确保部署安全，护栏（Guardrails）作为终态安全层被广泛应用，实时过滤输出并阻断有害行为。

## Enhancing AI Agent Capabilities

## 增强 AI 智能体

AI agents are systems that can perceive their environment and take autonomous actions to achieve goals. Their effectiveness is enhanced by robust reasoning frameworks.

AI 智能体是感知环境并采取自主行动以实现目标的智能系统。其效能通过强大的推理框架显著提升。

**Chain of Thought (CoT):** This prompting technique encourages a model to explain its reasoning step-by-step before giving a final answer. This process of "thinking out loud" often leads to more accurate results on complex reasoning tasks.

**思维链（Chain of Thought, CoT）：** 该提示技术引导模型在给出最终答案前逐步展示推理过程。此类"显式思考"机制常在复杂推理任务中产生更精确结果。

**Tree of Thoughts (ToT):** Tree of Thoughts is an advanced reasoning framework where an agent explores multiple reasoning paths simultaneously, like branches on a tree. It allows the agent to self-evaluate different lines of thought and choose the most promising one to pursue, making it more effective at complex problem-solving.

**思维树（Tree of Thoughts, ToT）：** 思维树是进阶推理框架，智能体同步探索多条推理路径（如树枝分叉）。该框架支持智能体评估不同思路质量，择优推进最有希望的路径，极大增强复杂问题解决效能。

**ReAct (Reason and Act):** ReAct is an agent framework that combines reasoning and acting in a loop. The agent first "thinks" about what to do, then takes an "action" using a tool, and uses the resulting observation to inform its next thought, making it highly effective at solving complex tasks.

**ReAct（推理-行动框架，Reason and Act）：** ReAct 是将推理与工具使用融合于循环流程的智能体框架。智能体先进行"思考"确定行动方向，随后通过工具执行"行动"，并依据执行结果"观察"调整后续思考，该机制在复杂任务解决中表现卓越。

**Planning:** This is an agent's ability to break down a high-level goal into a sequence of smaller, manageable sub-tasks. The agent then creates a plan to execute these steps in order, allowing it to handle complex, multi-step assignments.

**规划（Planning）：** 指智能体将目标分解为系列可管理子任务的能力。智能体据此制定执行计划并按序推进步骤，从而胜任复杂的多阶段任务。

**Deep Research:** Deep research refers to an agent's capability to autonomously explore a topic in-depth by iteratively searching for information, synthesizing findings, and identifying new questions. This allows the agent to build a comprehensive understanding of a subject far beyond a single search query.

**深度研究（Deep Research）：** 深度研究指智能体迭代式信息检索、发现整合与新问题识别，实现对主题的自主深入探索能力。这使得智能体超越单次查询范围，获得全面的主题认知。

**Critique Model:** A critique model is a specialized AI model trained to review, evaluate, and provide feedback on the output of another AI model. It acts as an automated critic, helping to identify errors, improve reasoning, and ensure the final output meets a desired quality standard.

**评判模型（Critique Model）：** 评判模型是经专门训练的 AI 模型，用于审查、评估并对其他 AI 模型输出提供反馈。其扮演自动化评审者角色，协助识别错误、优化推理流程并确保最终输出符合预期质量标准。
