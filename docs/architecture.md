# Architecture

```
                PDF / HWP
                    │
                    ▼
            Text Extraction
                    │
                    ▼
            Document Cleaner
                    │
                    ▼
          Hierarchy Parser
                    │
                    ▼
         Regulation Objects
                    │
         ┌──────────┴─────────┐
         ▼                    ▼
    Markdown             JSON
         │                    │
         └──────────┬─────────┘
                    ▼
             Knowledge Base
                    │
         ┌──────────┴─────────┐
         ▼                    ▼
      BM25                Embedding
         │                    │
         └──────────┬─────────┘
                    ▼
                  LLM
```

Parser is the core of the project.

LLM is only the final interface.
