# Proactive-RAG-Onboarding-Agent

**A cutting-edge Retrieval-Augmented Generation (RAG) agent built with LangChain to synthesize tailored, structured 30-day curricula for new corporate hires.**

## 🌟 Project Overview

This project tackles a common business challenge: **information overload** during employee onboarding. Instead of providing a static knowledge base, the **Proactive-RAG-Onboarding-Agent** leverages advanced Generative AI to act as a personalized curriculum planner.

It dynamically creates a step-by-step, 30-day learning and task agenda based on a new hire's specific **role** and **seniority**. This project demonstrates mastery of **Advanced RAG Architectures** and **Agent Orchestration**—key skills for any modern AI/ML Engineer.

### Key Value Proposition

  * **Personalization:** Generates unique content for roles like "Junior Backend Developer" vs. "Senior Data Scientist."
  * **Trust & Accuracy:** All tasks are **grounded** with direct citations to specific internal documents, virtually eliminating hallucinations.
  * **Efficiency:** Drastically reduces the time new employees spend searching for relevant information.

-----

## 🚀 Advanced Technical Features (Why this Project Stands Out)

This system is built to showcase several high-impact, advanced Generative AI techniques:

1.  **Dual-Retriever Architecture:** The core intelligence relies on orchestrating two parallel retrieval mechanisms:
      * **Task-Based Retriever:** Uses **metadata filtering** (`role_tag`, `topic_tag`) in the Vector Store to retrieve highly specific content (e.g., Python code standards, AWS setup guides).
      * **Persona-Based Retriever:** Uses standard semantic search to retrieve general examples of past successful onboarding plans to guide the final output *structure*.
2.  **Proactive Structured Generation:** The agent is designed for a complex generative task, not just reactive Q\&A. It is explicitly instructed to synthesize and sequence information into a cohesive schedule.
3.  **Pydantic Schema Validation:** Utilizes LangChain's **`PydanticOutputParser`** to strictly enforce the output format as a machine-readable JSON object (the `OnboardingPlan` schema). This ensures the output is reliable and production-ready for integration into HR systems.
4.  **LCEL Orchestration:** The entire workflow—from user input through dual retrieval, prompt construction, and output parsing—is chained together using the flexible and performant **LangChain Expression Language (LCEL)**.

-----

## 🛠️ Technology Stack

  * **Orchestration:** LangChain (LCEL, Agents, Custom Chains)
  * **Vector Database:** ChromaDB (for production-scale metadata filtering)
  * **LLM:** OpenAI (GPT-4)
  * **Embeddings:** `text-embedding-3-small` or BGE
  * **Frontend/UI:** React.js/Next.js
  * **Data Structures:** Pydantic

-----

## ⚙️ Setup and Installation

### Prerequisites

  * Python 3.9+
  * An OpenAI API Key (or credentials for your chosen LLM)

-----
That's great\! Including collaborators makes a project even more impressive. Here is the modified **Contribution and Contact** section, formatted correctly for your README.

-----

## 🤝 Contribution and Contact

Feel free to fork this repository, explore the advanced RAG techniques, and submit pull requests. We welcome contributions, feedback, and discussion\!

| Name | Contact | Email |
| :--- | :--- | :--- |
| **Keval Rajpal** | [Linkedin](https://linkedin.com/in/keval-rajpal) | kevalrajpal2580@gmail.com |
| **Muskan Gangwani** | [Linkedin](https://linkedin.com/in/muskan-gangwani) | muskan.r.gangwani@gmail.com
 |
 
-----   