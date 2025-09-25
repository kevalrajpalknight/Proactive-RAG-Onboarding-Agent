# Proactive-RAG-Onboarding-Agent
# Proactive RAG Onboarding Agent

Proactive RAG Agent for Tailored Corporate Onboarding: Generates structured, role-specific 30-day curricula grounded in internal documentation using LangChain and Advanced Metadata Filtering.

## Overview

The Proactive RAG Onboarding Agent synthesizes tailored 30-day curricula for new hires by leveraging:

- **Dual-Retriever Architecture**: Combines semantic similarity (vector embeddings) with metadata filtering for precise document retrieval
- **LangChain Integration**: Uses advanced language models for structured curriculum generation
- **Pydantic Validation**: Ensures output quality and structure with comprehensive data validation
- **Source Citations**: Tracks and validates all information sources to eliminate hallucination
- **Metadata Filtering**: Intelligently filters documents by role, department, seniority, and document type
- **Comprehensive Export**: Generates professional curriculum documents in Markdown and JSON formats

## Features

✅ **Smart Document Processing**: Automatically processes PDF, Word, Excel, PowerPoint, and text documents  
✅ **Role-Specific Curricula**: Generates customized 30-day plans based on role, department, and seniority  
✅ **Dual Retrieval System**: Semantic search + metadata filtering for accurate content retrieval  
✅ **Source Validation**: Every curriculum item includes verified source citations  
✅ **Quality Metrics**: Confidence scores and validation checks ensure curriculum quality  
✅ **CLI Interface**: Easy-to-use command-line tools for document management and curriculum generation  
✅ **Flexible Export**: Output to Markdown, JSON, or structured data formats  
✅ **Extensible Architecture**: Modular design allows easy customization and integration  

## Installation

### Prerequisites

- Python 3.9 or higher
- OpenAI API key (for LLM-powered curriculum generation)

### Install from PyPI (coming soon)

```bash
pip install proactive-rag-onboarding-agent
```

### Install from Source

```bash
git clone https://github.com/kevalrajpalknight/Proactive-RAG-Onboarding-Agent.git
cd Proactive-RAG-Onboarding-Agent
pip install -e .
```

### Set up Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"
```

## Quick Start

### 1. Initialize Configuration

```bash
onboarding-agent init-config --output config.yaml
```

Edit the generated `config.yaml` file and add your API keys and preferred settings.

### 2. Add Company Documents

```bash
# Add documents from a directory
onboarding-agent add-documents ./company-docs/

# Add specific files
onboarding-agent add-documents policy.pdf handbook.md training-guide.docx
```

### 3. Generate a Curriculum

```bash
# Generate curriculum for a junior software engineer
onboarding-agent generate "Software Engineer" "Engineering" \
  --seniority junior \
  --employee-id EMP-001 \
  --output junior-engineer-curriculum.md

# Generate for different roles
onboarding-agent generate "Sales Representative" "Sales" --seniority mid
onboarding-agent generate "Product Manager" "Product" --seniority senior
```

### 4. Search Knowledge Base

```bash
# Search for specific topics
onboarding-agent search "onboarding checklist" --top-k 5

# Filter by department
onboarding-agent search "training requirements" --department Engineering
```

### 5. Check System Status

```bash
onboarding-agent status
```

## Programmatic Usage

```python
import asyncio
from proactive_rag_agent import OnboardingAgent
from proactive_rag_agent.config import AgentConfig

async def generate_curriculum():
    # Initialize agent
    config = AgentConfig()  # Uses default configuration
    agent = OnboardingAgent(config=config)
    await agent.initialize()
    
    # Add documents
    await agent.add_documents(["./company-docs/"])
    
    # Generate curriculum
    curriculum = await agent.generate_curriculum(
        role_title="Software Engineer",
        department="Engineering",
        seniority_level="junior"
    )
    
    print(f"Generated {curriculum.total_estimated_hours:.1f} hours of curriculum")
    print(f"Using {len(curriculum.get_all_sources())} source documents")
    
    # Export to file
    from proactive_rag_agent.utils import export_curriculum_to_markdown
    export_curriculum_to_markdown(curriculum, "my-curriculum.md")
    
    await agent.close()

# Run the example
asyncio.run(generate_curriculum())
```

## Architecture

### Dual-Retriever System

The agent uses a sophisticated dual-retriever architecture:

1. **Semantic Retriever**: Uses sentence transformers and FAISS for vector similarity search
2. **Metadata Retriever**: Filters documents by structured metadata (role, department, type, etc.)
3. **Fusion Layer**: Combines results using weighted scoring, reciprocal rank fusion, or max scoring

### Document Processing Pipeline

1. **Ingestion**: Loads documents from various formats (PDF, Word, Excel, etc.)
2. **Preprocessing**: Extracts text, cleans content, and chunks for optimal retrieval
3. **Metadata Extraction**: Automatically extracts topics, keywords, target roles, and departments
4. **Indexing**: Creates both semantic embeddings and metadata indices
5. **Caching**: Intelligent caching system avoids reprocessing unchanged documents

### Curriculum Generation

1. **Context Retrieval**: Finds relevant documents based on role and department
2. **Outline Generation**: Creates high-level curriculum structure using LLM
3. **Detailed Planning**: Generates specific daily tasks with learning objectives
4. **Source Attribution**: Links every task to source documents
5. **Validation**: Comprehensive validation of structure, timing, and quality
6. **Export**: Professional formatting with citations and metrics

## Configuration

The agent supports extensive configuration through YAML files or environment variables:

```yaml
# config.yaml
llm:
  model_name: "gpt-3.5-turbo"
  temperature: 0.1
  max_tokens: 2000

retriever:
  semantic_model: "all-MiniLM-L6-v2"
  semantic_weight: 0.6
  metadata_weight: 0.4
  fusion_method: "weighted_sum"

curriculum:
  weeks_count: 4
  max_hours_per_day: 8.0
  require_weekly_assessments: true
  
paths:
  documents_path: "./data/documents"
  index_path: "./data/indices"
  cache_path: "./data/cache"
```

## Document Types and Metadata

The agent automatically categorizes documents and extracts metadata:

### Supported Document Types
- **Policy Documents**: Company policies, procedures, compliance guides
- **Training Materials**: Onboarding guides, training manuals, tutorials  
- **Technical Documentation**: API docs, system guides, architecture documents
- **Templates and Forms**: Checklists, forms, templates
- **Presentations**: Training slides, overview presentations

### Automatic Metadata Extraction
- **Topics and Keywords**: Automatically identified from content
- **Target Roles**: Inferred from document content and naming
- **Departments**: Extracted from file paths and content
- **Document Freshness**: Tracked for relevance scoring
- **Importance Scoring**: Based on document type, length, and update frequency

## Validation and Quality Assurance

### Curriculum Validation
- ✅ **Structure Validation**: Ensures 4-week structure with appropriate task distribution
- ✅ **Time Validation**: Checks realistic time allocation (80-200 hours total)
- ✅ **Source Validation**: Verifies all tasks have proper source citations
- ✅ **Content Quality**: Validates learning objectives, assessments, and progression
- ✅ **Completeness**: Ensures all required components are present

### Source Citation Tracking
- Every task links to specific source documents
- Source relevance and confidence scores tracked
- Automatic detection of hallucinated content
- Citation formatting and validation

## Example Output

The agent generates comprehensive curricula like this:

```markdown
# 30-Day Onboarding Curriculum

**Role:** Software Engineer  
**Department:** Engineering  
**Seniority Level:** Junior  
**Total Estimated Hours:** 152.5  

## Week 1: Company Orientation and Setup

### Learning Goals
- Complete initial setup and paperwork
- Understand company culture and values  
- Meet key team members

### Monday
**Company Overview and Culture** (120 min)
- Type: Training
- Description: Introduction to TechCorp values, mission, and culture
- Learning Objectives:
  - Understand company mission and values
  - Learn about organizational structure
- Sources: [Employee Handbook](link), [Company Overview](link)
```

## API Reference

### Core Classes

- **`OnboardingAgent`**: Main orchestrator class
- **`DualRetriever`**: Handles document retrieval with semantic + metadata search  
- **`CurriculumGenerator`**: Generates structured curriculum plans using LLM
- **`DocumentProcessor`**: Processes and indexes documents
- **`CurriculumPlan`**: Pydantic model for validated curriculum structure

### Configuration Classes

- **`AgentConfig`**: Main configuration container
- **`LLMConfig`**: Language model settings
- **`RetrieverConfig`**: Retrieval system configuration
- **`CurriculumConfig`**: Curriculum generation parameters

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/kevalrajpalknight/Proactive-RAG-Onboarding-Agent.git
cd Proactive-RAG-Onboarding-Agent
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black proactive_rag_agent/
isort proactive_rag_agent/
flake8 proactive_rag_agent/
mypy proactive_rag_agent/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] **Integration Connectors**: Slack, Teams, SharePoint, Confluence
- [ ] **Multi-language Support**: Support for non-English documents and curricula
- [ ] **Advanced Analytics**: Learning analytics and curriculum effectiveness tracking
- [ ] **Template Library**: Pre-built curriculum templates for common roles
- [ ] **Interactive Delivery**: Integration with LMS platforms for curriculum delivery
- [ ] **Feedback Loop**: Automatic curriculum improvement based on employee feedback

## Support

- **Documentation**: Full documentation at [docs link]
- **Issues**: Report bugs and request features on [GitHub Issues](issues-link)
- **Discussions**: Join our community discussions on [GitHub Discussions](discussions-link)

## Acknowledgments

Built with:
- [LangChain](https://langchain.com/) for LLM orchestration
- [Pydantic](https://pydantic.dev/) for data validation
- [FAISS](https://faiss.ai/) for vector similarity search
- [Sentence Transformers](https://www.sbert.net/) for semantic embeddings
- [Typer](https://typer.tiangolo.com/) for CLI interface
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
