"""Command-line interface for the Proactive RAG Onboarding Agent."""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel
from rich.text import Text

from .core.agent import OnboardingAgent
from .config import load_config, create_example_config
from .utils import setup_logging, export_curriculum_to_markdown, export_curriculum_to_json
from .models import FilterCriteria, DocumentType

# Initialize CLI app and console
app = typer.Typer(
    name="onboarding-agent",
    help="Proactive RAG Onboarding Agent - Generate tailored 30-day curricula",
    no_args_is_help=True
)
console = Console()


@app.command()
def init_config(
    output_path: str = typer.Option(
        "config.yaml",
        "--output", "-o",
        help="Output path for configuration file"
    )
):
    """Initialize a configuration file with example values."""
    
    try:
        create_example_config(output_path)
        console.print(f"✅ Configuration template created: {output_path}", style="green")
        console.print("📝 Edit the configuration file and add your API keys before using the agent.")
    except Exception as e:
        console.print(f"❌ Failed to create configuration: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def add_documents(
    paths: List[str] = typer.Argument(..., help="Paths to documents or directories"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reprocessing of cached documents"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Add documents to the knowledge base."""
    
    setup_logging("DEBUG" if verbose else "INFO")
    
    async def _add_documents():
        try:
            # Load configuration
            config = load_config(config_path)
            
            # Initialize agent
            agent = OnboardingAgent(config=config)
            await agent.initialize()
            
            console.print("📚 Processing documents...", style="blue")
            
            # Add documents
            results = await agent.add_documents(paths, force_reindex=force)
            
            if results['success']:
                console.print(f"✅ Successfully processed {results['processed_count']} documents", style="green")
                
                # Display stats
                stats = results.get('retriever_stats', {})
                if stats:
                    table = Table(title="Knowledge Base Statistics")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    
                    semantic_stats = stats.get('semantic_retriever', {})
                    if semantic_stats:
                        table.add_row("Total Documents", str(semantic_stats.get('total_documents', 0)))
                        table.add_row("Index Size", str(semantic_stats.get('index_size', 0)))
                        table.add_row("Embedding Model", semantic_stats.get('model_name', 'N/A'))
                    
                    console.print(table)
            else:
                console.print(f"❌ Failed to process documents: {results.get('message', 'Unknown error')}", style="red")
                raise typer.Exit(1)
                
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
            raise typer.Exit(1)
        finally:
            if 'agent' in locals():
                await agent.close()
    
    asyncio.run(_add_documents())


@app.command() 
def generate(
    role: str = typer.Argument(..., help="Target role title"),
    department: str = typer.Argument(..., help="Department"),
    seniority: str = typer.Option("junior", "--seniority", "-s", help="Seniority level (junior/mid/senior)"),
    employee_id: Optional[str] = typer.Option(None, "--employee-id", "-e", help="Employee ID"),
    output: str = typer.Option("curriculum.md", "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown/json)"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Generate a 30-day onboarding curriculum."""
    
    setup_logging("DEBUG" if verbose else "INFO")
    
    async def _generate():
        try:
            # Load configuration
            config = load_config(config_path)
            
            # Initialize agent
            agent = OnboardingAgent(config=config)
            await agent.initialize()
            
            # Check if documents are loaded
            stats = agent.get_stats()
            if not stats.get('documents_loaded', False):
                console.print("❌ No documents loaded. Use 'add-documents' command first.", style="red")
                raise typer.Exit(1)
            
            console.print("🤖 Generating curriculum...", style="blue")
            
            # Generate curriculum
            curriculum = await agent.generate_curriculum(
                role_title=role,
                department=department,
                seniority_level=seniority,
                employee_id=employee_id
            )
            
            # Export curriculum
            if format.lower() == "json":
                output_path = export_curriculum_to_json(curriculum, output)
            else:
                output_path = export_curriculum_to_markdown(curriculum, output)
            
            console.print(f"✅ Curriculum generated successfully!", style="green")
            console.print(f"📄 Saved to: {output_path}")
            
            # Display summary
            panel_content = f"""
**Role:** {curriculum.role_title}
**Department:** {curriculum.department}
**Seniority:** {curriculum.seniority_level}
**Total Hours:** {curriculum.total_estimated_hours:.1f}
**Sources:** {len(curriculum.get_all_sources())}
**Confidence:** {curriculum.confidence_score:.2f}
            """.strip()
            
            console.print(Panel(panel_content, title="Curriculum Summary", style="green"))
            
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
            raise typer.Exit(1)
        finally:
            if 'agent' in locals():
                await agent.close()
    
    asyncio.run(_generate())


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of results to return"),
    department: Optional[str] = typer.Option(None, "--department", "-d", help="Filter by department"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Filter by role"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Search documents in the knowledge base."""
    
    setup_logging("DEBUG" if verbose else "INFO")
    
    async def _search():
        try:
            # Load configuration
            config = load_config(config_path)
            
            # Initialize agent
            agent = OnboardingAgent(config=config)
            await agent.initialize()
            
            # Create filters if specified
            filters = None
            if department or role:
                filters = FilterCriteria(
                    department=department,
                    target_role=role
                )
            
            console.print(f"🔍 Searching for: '{query}'", style="blue")
            
            # Search documents
            results = await agent.search_documents(
                query=query,
                filters=filters,
                top_k=top_k
            )
            
            if not results:
                console.print("No results found.", style="yellow")
                return
            
            # Display results
            for i, result in enumerate(results, 1):
                source = result['source']
                console.print(f"\n📄 Result {i}", style="bold blue")
                console.print(f"Title: {source['title']}")
                console.print(f"Type: {source['document_type']}")
                console.print(f"Relevance: {result['relevance_score']:.3f}")
                if source.get('department'):
                    console.print(f"Department: {source['department']}")
                console.print(f"Content: {result['content'][:200]}...")
                console.print("-" * 50)
                
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
            raise typer.Exit(1)
        finally:
            if 'agent' in locals():
                await agent.close()
    
    asyncio.run(_search())


@app.command()
def status(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """Show agent status and statistics."""
    
    async def _status():
        try:
            # Load configuration
            config = load_config(config_path)
            
            # Initialize agent
            agent = OnboardingAgent(config=config)
            await agent.initialize()
            
            # Get health check
            health = await agent.health_check()
            
            # Display status
            status_color = "green" if health['status'] == 'healthy' else "red"
            console.print(f"🏥 Agent Status: {health['status']}", style=status_color)
            
            # Component status table
            table = Table(title="Component Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="white")
            
            for component, info in health['components'].items():
                status = info.get('status', 'unknown')
                details = []
                
                if component == 'retriever':
                    if 'total_documents' in info:
                        details.append(f"Documents: {info['total_documents']}")
                elif component == 'llm':
                    if 'model' in info:
                        details.append(f"Model: {info['model']}")
                
                table.add_row(component.title(), status, " | ".join(details))
            
            console.print(table)
            
            # Get detailed stats if available
            stats = agent.get_stats()
            if stats.get('retriever'):
                retriever_stats = stats['retriever']
                
                console.print("\n📊 Knowledge Base Statistics", style="bold blue")
                semantic_stats = retriever_stats.get('semantic_retriever', {})
                metadata_stats = retriever_stats.get('metadata_retriever', {})
                
                if semantic_stats:
                    console.print(f"Semantic Index: {semantic_stats.get('total_documents', 0)} documents")
                    console.print(f"Embedding Model: {semantic_stats.get('model_name', 'N/A')}")
                
                if metadata_stats:
                    console.print(f"Metadata Index: {metadata_stats.get('total_documents', 0)} documents")
                    console.print(f"Topics: {metadata_stats.get('unique_topics', 0)}")
                    console.print(f"Keywords: {metadata_stats.get('unique_keywords', 0)}")
                
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
            raise typer.Exit(1)
        finally:
            if 'agent' in locals():
                await agent.close()
    
    asyncio.run(_status())


@app.command()
def validate(
    curriculum_file: str = typer.Argument(..., help="Path to curriculum JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed validation results")
):
    """Validate a curriculum file."""
    
    from .utils.validation import validate_curriculum
    from .models import CurriculumPlan
    
    try:
        # Load curriculum
        with open(curriculum_file, 'r') as f:
            curriculum_data = json.load(f)
        
        curriculum = CurriculumPlan(**curriculum_data)
        
        # Validate
        console.print("🔍 Validating curriculum...", style="blue")
        results = validate_curriculum(curriculum)
        
        # Display results
        if results['valid']:
            console.print("✅ Curriculum is valid!", style="green")
        else:
            console.print("❌ Curriculum has validation issues:", style="red")
            
            if results['errors']:
                console.print("\n🚨 Errors:", style="red bold")
                for error in results['errors']:
                    console.print(f"  • {error}", style="red")
        
        if results['warnings']:
            console.print("\n⚠️  Warnings:", style="yellow bold")
            for warning in results['warnings']:
                console.print(f"  • {warning}", style="yellow")
        
        if verbose and results['scores']:
            console.print("\n📊 Quality Scores:", style="blue bold")
            for metric, score in results['scores'].items():
                console.print(f"  • {metric}: {score:.2f}", style="white")
        
        if results['suggestions']:
            console.print("\n💡 Suggestions:", style="cyan bold")
            for suggestion in results['suggestions']:
                console.print(f"  • {suggestion}", style="cyan")
        
    except FileNotFoundError:
        console.print(f"❌ File not found: {curriculum_file}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()