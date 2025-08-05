"""
Test logger integration in Decomposer Agent.
"""
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.decomposer_agent import DecomposerAgent
from utils.models import ChatMessage

# 设置日志级别为DEBUG以查看所有日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_logger_integration():
    """测试logger集成是否正常工作"""
    print("=== Testing Logger Integration ===\n")
    
    agent = DecomposerAgent(agent_name="LoggerTestDecomposer", dataset_name="generic")
    
    # 创建一个会触发LLM失败的测试消息（通过设置无效的API key）
    message = ChatMessage(
        db_id="test_db",
        query="Show all products",
        desc_str="# Table: products\n[id, name, price]",
        fk_str="",
        evidence=""
    )
    
    print("Processing message to test logger integration...")
    print("Note: You should see logger messages in the output below.\n")
    
    try:
        response = agent.talk(message)
        print(f"Response success: {response.success}")
        if response.success:
            print(f"Generated SQL: {message.final_sql}")
        else:
            print(f"Error: {response.error}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")
    
    print("\n=== Logger Integration Test Complete ===")
    print("✅ If you see logger messages above, the integration is working correctly!")

if __name__ == "__main__":
    test_logger_integration()