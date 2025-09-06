# Technical Approach: AI Medical Scheduling Agent
**Prepared for:** Raga.AI  
**Prepared by:** Kadali Harshavardhan  
**Date:** September 3, 2025

## 1. Architecture Overview: A Multi-Agent Graph Design

The proposed solution is an intelligent, multi-agent system designed using a stateful graph architecture. This approach provides a robust and scalable framework for handling the complex, multi-turn conversation required for medical appointment scheduling. The core of the system is a state machine that transitions between different nodes based on the conversation's context and the output of various tools.

The primary components of the architecture are:

**State Graph (The "Nervous System"):** Built with LangGraph, this graph manages the flow of the conversation. It holds the AgentState, which acts as the "memory" of the interaction, storing messages and collected patient data.

**Primary Agent (The "Brain"):** A Large Language Model (LLM) powered by the OpenAI API (via langchain-openai). This agent is the central decision-maker. It processes user input, decides which tool to use, and formulates responses.

**Tool Belt (The "Hands and Eyes"):** A collection of deterministic Python functions that allow the agent to interact with the outside world (our data files). This includes tools for looking up patients, finding available appointments, and booking them.

**Router Node (The "Traffic Controller"):** A crucial node within the graph that inspects the agent's output. If the agent decides to use a tool, the router directs the state to the tool execution node. If the agent decides to respond to the user, the router ends the current turn.

This graph-based design ensures that the agent follows a predictable, logical workflow while still allowing for the flexibility needed to handle natural language conversations.

## 2. Framework Choice: LangGraph + LangChain

For this assignment, I have chosen **Option 1: LangGraph + LangChain**.

**Justification:**

While a dedicated Agent Development Toolkit (ADK) can offer faster initial setup, the LangGraph and LangChain combination provides a far more powerful, flexible, and transparent framework for building a production-grade AI agent.

**Granular Control:** LangGraph gives me precise control over the agent's workflow. I can explicitly define the nodes (steps) and edges (transitions), which is essential for building a reliable system that must follow a specific business logic, such as determining appointment duration based on patient status.

**Enhanced Debuggability:** The graph structure makes it much easier to trace the agent's "thought process." I can see exactly which node was executed, what tool was called, and what the output was at every step. This is invaluable for debugging and refining the agent's behavior.

**Extensibility and Scalability:** The LangChain ecosystem is model-agnostic and has a vast library of integrations. This architecture is not a black box; it's a scalable foundation that could easily be extended in the future to integrate with real EMR APIs, different calendar systems, or more advanced LLMs without a complete rewrite. It is the more professional and forward-looking choice.

## 3. Integration Strategy

The agent will interact with the provided mock data sources through a set of well-defined tools:

**Patient Data (EMR):** The patients.csv file will be read using the pandas library. A lookup_patient tool will allow the agent to query this data to find patients and determine if they are new or returning.

**Calendar Management (Schedules):** The schedules.xlsx file will also be managed with pandas. A find_available_slots tool will read the schedule, filter for the correct doctor and date, and identify open time slots. A book_appointment tool will then update the is_booked status in the DataFrame and overwrite the Excel file to persist the change.

**Communication (Email & SMS):** While a full email/SMS integration is outside the scope of the MVP, the logic will be implemented with placeholder functions. The agent will call these functions at the correct point in the workflow (after a successful booking), demonstrating that the integration points are correctly designed.

**Data Export (Admin Review):** A dedicated tool will be created to generate the final appointment confirmation as an Excel file, which will be saved to an exports directory.

## 4. Challenges & Solutions

**Challenge:** Ensuring the agent reliably follows the multi-step business logic without getting stuck in a loop or hallucinating.

**Solution:** A highly detailed system prompt will be provided to the agent, explicitly outlining the required step-by-step workflow. The stateful nature of the LangGraph will ensure that critical information (like patient status) is remembered across turns, guiding the agent's decisions.

**Challenge:** Structuring the data collected from the user (name, DOB, insurance info) in a reliable format.

**Solution:** I will use Pydantic models in conjunction with the LLM's tool-calling ability. The model will be prompted to structure its output to fit these predefined data models, ensuring that the data passed to our tools is always clean, validated, and in the correct format, which significantly reduces the chance of errors.

**Challenge:** Handling different appointment durations (60 minutes for new patients, 30 minutes for returning patients) while maintaining calendar integrity.

**Solution:** Implemented a duration-aware Calendly simulation that intelligently merges consecutive 30-minute slots for 60-minute appointments. The system uses slot pairing logic with `calendly_pair_i_j` IDs to ensure atomic booking of merged slots, preventing double-booking scenarios.

**Challenge:** Managing conversation state and preventing data loss during multi-turn interactions.

**Solution:** The LangGraph state management system maintains persistent conversation history and patient context across turns. The AgentState TypedDict ensures critical information like patient details and booking status are preserved throughout the interaction.

**Challenge:** Ensuring reliable tool execution and error handling in a production environment.

**Solution:** Implemented comprehensive error handling with try-catch blocks around all tool executions. Each tool returns structured responses with success/error indicators, and the agent can gracefully handle failures by providing meaningful feedback to users.

**Challenge:** Simulating real-world integrations (Calendly, email, SMS) while maintaining system reliability.

**Solution:** Created mock implementations that mirror real API structures and behaviors. The system includes toggles for real vs. simulated services, allowing seamless transition to production APIs. Form handling includes actual PDF reading and email attachment preparation.

**Challenge:** Providing administrative oversight and reporting capabilities.

**Solution:** Implemented automated appointment logging to Excel with normalized schemas, plus on-demand admin report generation that provides both summary statistics and raw data views for clinic management review.

**Challenge:** Handling edge cases in date parsing and time slot management.

**Solution:** Built robust date normalization functions that handle multiple input formats, and implemented adjacency checking for slot merging with tolerance for minor time gaps. The system includes comprehensive validation for all user inputs.

**Challenge:** Maintaining data consistency across multiple file operations and concurrent access.

**Solution:** Implemented atomic file operations with proper error rollback mechanisms. The system uses pandas DataFrame operations with immediate Excel persistence to ensure data integrity, and includes validation checks before committing changes.

**Challenge:** Creating an intuitive user interface that handles complex conversation flows.

**Solution:** Developed a clean, ChatGPT-like Streamlit interface with proper message threading, input validation, and real-time feedback. The UI hides internal tool operations while providing clear visual indicators for booking success and system status.
