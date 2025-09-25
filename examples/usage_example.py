#!/usr/bin/env python3
"""
Example usage of the Proactive RAG Onboarding Agent.

This script demonstrates how to use the agent programmatically to:
1. Initialize the agent
2. Add documents to the knowledge base
3. Generate a curriculum
4. Export the results
"""

import asyncio
import os
from pathlib import Path

from proactive_rag_agent import OnboardingAgent
from proactive_rag_agent.config import AgentConfig
from proactive_rag_agent.utils import setup_logging, export_curriculum_to_markdown


async def main():
    """Main example function."""
    
    # Set up logging
    setup_logging("INFO")
    
    # Create configuration (you would normally load this from a file)
    config = AgentConfig(
        # Note: In real usage, set your OpenAI API key in environment variable
        # or configuration file
        documents_path="./examples/sample_documents",
        index_path="./data/indices",
        cache_path="./data/cache"
    )
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set your OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return
    
    try:
        # Initialize the agent
        print("🤖 Initializing Proactive RAG Onboarding Agent...")
        agent = OnboardingAgent(config=config)
        await agent.initialize()
        
        # Add sample documents to the knowledge base
        print("📚 Adding documents to knowledge base...")
        sample_docs_path = Path("./examples/sample_documents")
        
        if sample_docs_path.exists():
            document_paths = [str(sample_docs_path)]
            results = await agent.add_documents(document_paths)
            
            if results['success']:
                print(f"✅ Successfully processed {results['processed_count']} documents")
                
                # Display retriever statistics
                stats = results.get('retriever_stats', {})
                if stats:
                    semantic_stats = stats.get('semantic_retriever', {})
                    print(f"📊 Knowledge base contains {semantic_stats.get('total_documents', 0)} documents")
            else:
                print(f"❌ Failed to process documents: {results.get('message', 'Unknown error')}")
                return
        else:
            print("⚠️  Sample documents not found. Creating knowledge base without documents for demo.")
        
        # Generate a curriculum for a new software engineer
        print("\n🎯 Generating curriculum for Junior Software Engineer...")
        curriculum = await agent.generate_curriculum(
            role_title="Software Engineer",
            department="Engineering", 
            seniority_level="junior",
            employee_id="EMP-001"
        )
        
        print("✅ Curriculum generated successfully!")
        print(f"📈 Curriculum Details:")
        print(f"   • Total hours: {curriculum.total_estimated_hours:.1f}")
        print(f"   • Number of sources: {len(curriculum.get_all_sources())}")
        print(f"   • Confidence score: {curriculum.confidence_score:.2f}")
        print(f"   • Source coverage: {curriculum.source_coverage:.2f}")
        
        # Validate the curriculum
        from proactive_rag_agent.utils.validation import validate_curriculum
        validation_results = validate_curriculum(curriculum)
        
        if validation_results['valid']:
            print("✅ Curriculum validation passed")
        else:
            print("⚠️  Curriculum has validation issues:")
            for error in validation_results['errors']:
                print(f"   • Error: {error}")
            for warning in validation_results['warnings']:
                print(f"   • Warning: {warning}")
        
        # Export curriculum to markdown
        print("\n📄 Exporting curriculum...")
        output_path = export_curriculum_to_markdown(
            curriculum, 
            "example_curriculum.md",
            include_sources=True
        )
        print(f"✅ Curriculum exported to: {output_path}")
        
        # Search the knowledge base
        print("\n🔍 Testing document search...")
        search_results = await agent.search_documents(
            query="onboarding new employee first week",
            top_k=3
        )
        
        print(f"Found {len(search_results)} relevant documents:")
        for i, result in enumerate(search_results[:3], 1):
            source = result['source']
            print(f"   {i}. {source['title']} (relevance: {result['relevance_score']:.3f})")
        
        # Display agent status
        print("\n📊 Agent Status:")
        health = await agent.health_check()
        print(f"   • Overall status: {health['status']}")
        
        for component, info in health['components'].items():
            status = info.get('status', 'unknown')
            print(f"   • {component.title()}: {status}")
        
        print("\n🎉 Example completed successfully!")
        print("\nNext steps:")
        print("1. Add your own company documents to the knowledge base")
        print("2. Generate curricula for different roles and departments")
        print("3. Customize the configuration for your needs")
        print("4. Integrate with your HR systems")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        if 'agent' in locals():
            await agent.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())