#!/usr/bin/env python3

import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

def setup_pinecone():
    """Setup Pinecone index for conversation history"""
    
    # Load environment variables
    load_dotenv()
    
    # Get Pinecone credentials
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "conversation-history")
    
    if not api_key:
        print("❌ Error: PINECONE_API_KEY must be set in .env file")
        print("\nPlease create a .env file with:")
        print("PINECONE_API_KEY=your_api_key_here")
        print("PINECONE_INDEX_NAME=conversation-history")
        return False
    
    try:
        # Initialize Pinecone with new API
        pc = Pinecone(api_key=api_key)
        print(f"✅ Connected to Pinecone")
        
        # Check if index exists
        existing_indexes = pc.list_indexes()
        
        if index_name in existing_indexes.names():
            print(f"✅ Index '{index_name}' already exists")
            index = pc.Index(index_name)
            print(f"📊 Index stats: {index.describe_index_stats()}")
        else:
            print(f"🔧 Creating new index: {index_name}")
            
            # Create index with appropriate settings for sentence embeddings
            pc.create_index(
                name=index_name,
                dimension=384,  # all-MiniLM-L6-v2 dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            
            print(f"✅ Index '{index_name}' created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Pinecone: {e}")
        return False

def test_namespace_functionality():
    """Test namespace functionality for multi-user scenarios"""
    
    load_dotenv()
    
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "conversation-history")
    
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        
        print("\n🧪 Testing Namespace Functionality...")
        
        # Test data for different users
        test_users = ["user001", "user002", "user003"]
        test_vectors = [0.1] * 384  # 384-dimensional vector
        
        # Store test data in different namespaces
        for user_id in test_users:
            index.upsert(
                vectors=[{
                    'id': f'test_{user_id}',
                    'values': test_vectors,
                    'metadata': {
                        'user_prompt': f'Hello from {user_id}',
                        'ai_response': f'Response for {user_id}',
                        'timestamp': '2024-01-01T00:00:00'
                    }
                }],
                namespace=user_id
            )
            print(f"✅ Stored test data in namespace: {user_id}")
        
        # Test querying each namespace separately
        for user_id in test_users:
            results = index.query(
                vector=test_vectors,
                namespace=user_id,
                top_k=5,
                include_metadata=True
            )
            print(f"✅ Query in namespace {user_id}: Found {len(results.matches)} results")
            
            # Verify isolation - should only find data from this user's namespace
            for match in results.matches:
                if match.metadata['user_prompt'] != f'Hello from {user_id}':
                    print(f"❌ Data isolation failed for {user_id}")
                    return False
        
        # Test cross-namespace isolation
        print("\n🔒 Testing Cross-Namespace Isolation...")
        for user_id in test_users:
            # Query in one namespace but look for data from another
            other_user = next(u for u in test_users if u != user_id)
            results = index.query(
                vector=test_vectors,
                namespace=user_id,
                filter={"user_prompt": f"Hello from {other_user}"},
                top_k=5,
                include_metadata=True
            )
            
            if len(results.matches) > 0:
                print(f"❌ Cross-namespace isolation failed: {user_id} found {other_user}'s data")
                return False
            else:
                print(f"✅ Namespace {user_id} properly isolated from {other_user}")
        
        # Clean up test data
        for user_id in test_users:
            index.delete(ids=[f'test_{user_id}'], namespace=user_id)
            print(f"✅ Cleaned up namespace: {user_id}")
        
        print("\n🎉 All namespace tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Namespace test failed: {e}")
        return False

def test_pinecone_connection():
    """Test the Pinecone connection and basic operations"""
    
    load_dotenv()
    
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "conversation-history")
    
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        
        # Test basic operations
        print("🧪 Testing Pinecone operations...")
        
        # Test upsert
        test_vector = [0.1] * 384  # 384-dimensional vector
        index.upsert(vectors=[{
            'id': 'test_vector',
            'values': test_vector,
            'metadata': {
                'user_prompt': 'test prompt',
                'ai_response': 'test response',
                'timestamp': '2024-01-01T00:00:00'
            }
        }])
        print("✅ Upsert test passed")
        
        # Test query
        results = index.query(
            vector=test_vector,
            top_k=1,
            include_metadata=True
        )
        print("✅ Query test passed")
        
        # Clean up test data
        index.delete(ids=['test_vector'])
        print("✅ Delete test passed")
        
        print("🎉 All Pinecone tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Pinecone test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Pinecone Setup Script")
    print("=" * 40)
    
    # Setup Pinecone
    if setup_pinecone():
        print("\n🧪 Running connection tests...")
        if test_pinecone_connection():
            print("\n🧪 Running namespace tests...")
            test_namespace_functionality()
    else:
        print("\n❌ Setup failed. Please check your configuration.")