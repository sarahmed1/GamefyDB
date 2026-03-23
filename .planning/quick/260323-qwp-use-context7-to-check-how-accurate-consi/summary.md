# Planning Agent Accuracy and Consistency (LangGraph)

Based on documentation from Context7 for the **LangGraph** framework, ensuring accuracy and consistency in planning agents relies on several key architectural patterns:

## 1. Structured Output for Planning
To ensure a planning agent produces an accurate and parseable plan, you should augment the LLM with strict schemas using Pydantic and `.with_structured_output()`. 
By forcing the LLM to output a strictly typed schema (e.g., a list of `Section` objects containing a `name` and `description`), you guarantee that the orchestrator's output is consistently formatted for downstream worker agents to execute without parsing errors.

## 2. Deterministic Control Flow via Tasks
Planning agents often deal with human-in-the-loop interactions or interruptions. To maintain consistency when resuming a workflow, non-deterministic operations (like fetching the current time or random generation) should be encapsulated inside a `@task`. This ensures the result is cached, and upon workflow resumption, the agent uses the exact same value, preventing logic or branching errors during execution.

## 3. State Persistence and Checkpointing
Accuracy over long-running planning and execution cycles is managed through checkpointers (like `MemorySaver`). By passing `checkpointer=True` or a dedicated MemorySaver instance when creating agents and subagents, the framework saves and restores the agent's state across invocations. This ensures the agent accurately remembers previous steps and context without hallucinating past actions.

## 4. Orchestrator-Worker Separation
Consistent execution of plans is achieved by separating the "planner" from the "executor". An Orchestrator LLM handles structured output generation (the plan), and distinct worker nodes/agents handle the execution of individual sections. This modularity reduces the cognitive load on a single LLM, increasing overall accuracy.