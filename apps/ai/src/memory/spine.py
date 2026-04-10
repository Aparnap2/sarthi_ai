"""Memory Spine — unified entry point for all 5 layers."""
from __future__ import annotations
from typing import Any


class MemorySpine:
    def __init__(self):
        self.layers = []

    def add_layer(self, layer):
        self.layers.append(layer)

    def load_context(self, tenant_id: str, task: str, signal: dict,
                     max_tokens: int = 800) -> str:
        """Load context from all available layers."""
        results = []
        for layer in self.layers:
            if hasattr(layer, 'available') and not layer.available():
                continue
            try:
                if hasattr(layer, 'search'):
                    results.extend(layer.search(tenant_id, task))
                elif hasattr(layer, 'read'):
                    results.extend(layer.read(tenant_id, task))
            except Exception:
                continue

        from src.memory.rag_kernel import RAGKernel
        kernel = RAGKernel()
        sections = [
            f"[FOUNDER IDENTITY]\nTenant: {tenant_id}",
            f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in results[:5]]),
            f"[CURRENT SIGNAL]\n{signal}",
            f"[TASK]\n{task}",
        ]
        assembled = "\n\n".join(sections)
        while len(assembled) > max_tokens * 4 and results:
            results = results[:-1]
            sections[1] = f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in results])
            assembled = "\n\n".join(sections)
        return assembled
