import asyncio
from src.core.orchestrator import JarvisOrchestrator

from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory

async def run_tests():
    llm = LocalLLMClient()
    memory = KnowledgeMemory()
    orch = JarvisOrchestrator(llm=llm, memory=memory)
    print("TEST 3: Basic Chat")
    async for chunk in orch.process("Hello Jarvis"):
        print(chunk, end="", flush=True)
    print("\n\nTEST 4: ReAct Reasoning (Search)")
    async for chunk in orch.process("Search the web for the latest Python news and summarize it."):
        print(chunk, end="", flush=True)
    print("\n\nTEST 6: Code Execution")
    async for chunk in orch.process("python: print('Hello from Python Sandbox!')"):
        print(chunk, end="", flush=True)
    print("\nDONE")

if __name__ == "__main__":
    asyncio.run(run_tests())
