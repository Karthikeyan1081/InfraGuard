import os
import logging
from typing import List, Dict, Any

import openai
import pymongo
from google import genai


class AgentLLM:
    """Agent helper for indexing and summarizing discrepancies.

    Strictly relies on Cloud APIs (OpenAI or Gemini) for text summarization
    and embeddings, and MongoDB Atlas for vector storage. This avoids heavy
    local ML libraries.
    """

    def __init__(self, openai_model: str = "gpt-4o-mini"):
        self.llm_provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
        self.openai_model = openai_model

        # Vector DB Init
        self.mongo_client = None
        self.mongo_collection = None

        try:
            atlas_uri = os.environ.get("MONGODB_ATLAS_URI")
            if not atlas_uri:
                logging.warning("MONGODB_ATLAS_URI not set — Vector operations will fail.")
            else:
                self.mongo_client = pymongo.MongoClient(atlas_uri)
                self.mongo_collection = self.mongo_client.assetsync.discrepancies
        except Exception:
            logging.exception("MongoDB Atlas initialization failed — continuing without vector DB")

        # LLM Init
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_client = None
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        self.gemini_client = None
        if self.llm_provider == "gemini":
            if not self.gemini_key:
                logging.warning("GEMINI_API_KEY not set — Gemini operations will fail until configured.")
            else:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
        else:
            if not self.openai_key:
                logging.warning("OPENAI_API_KEY not set — OpenAI operations will fail until configured.")
            else:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Fetch embeddings for a list of texts using the selected API provider."""
        if not texts:
            return []
            
        if self.llm_provider == "gemini":
            if not self.gemini_client:
                raise RuntimeError("GEMINI_API_KEY is missing for embeddings.")
            # Default model for embeddings
            response = self.gemini_client.models.embed_content(
                model="text-embedding-004",
                contents=texts,
                config=genai.types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return [emb.values for emb in response.embeddings]
        else:
            if not self.openai_client:
                raise RuntimeError("OPENAI_API_KEY is missing for embeddings.")
            response = self.openai_client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [data.embedding for data in response.data]

    def _get_embedding(self, text: str) -> List[float]:
        """Fetch a single embedding."""
        if self.llm_provider == "gemini":
            if not self.gemini_client:
                raise RuntimeError("GEMINI_API_KEY is missing for embeddings.")
            response = self.gemini_client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=genai.types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            )
            return response.embeddings[0].values
        else:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding

    def index_discrepancies(self, items: List[Dict[str, Any]]):
        """Create / update vector index for given discrepancy items."""
        if not self.mongo_collection:
            logging.warning("Atlas collection unavailable — skipping indexing")
            return
            
        ids = []
        texts = []
        metadatas = []
        for it in items:
            ids.append(it.get("id") or it.get("uuid") or str(hash(str(it))))
            texts.append(it.get("description", ""))
            meta = {k: v for k, v in it.items() if k != "description"}
            metadatas.append(meta)

        try:
            embs = self._get_embeddings(texts)
        except Exception:
            logging.exception("Failed to fetch API embeddings")
            return

        docs_to_insert = []
        for i in range(len(ids)):
            doc = {"_id": ids[i], "description": texts[i], "metadata": metadatas[i]}
            if embs and i < len(embs):
                doc["embedding"] = embs[i]
            docs_to_insert.append(doc)
            
        try:
            from pymongo import UpdateOne
            ops = [UpdateOne({"_id": d["_id"]}, {"$set": d}, upsert=True) for d in docs_to_insert]
            if ops:
                self.mongo_collection.bulk_write(ops)
        except Exception:
            logging.exception("Atlas bulk write failed")

    def retrieve_similar(self, query: str, n: int = 3):
        """Return top-n similar items from the discrepancies collection."""
        if not self.mongo_collection:
            logging.warning("Atlas collection unavailable — retrieve_similar returning None")
            return None
            
        try:
            query_emb = self._get_embedding(query)
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_emb,
                        "numCandidates": n * 10,
                        "limit": n
                    }
                }
            ]
            return list(self.mongo_collection.aggregate(pipeline))
        except Exception:
            logging.exception("Atlas vector search failed")
            return None

    def summarize_discrepancies(self, items: List[Dict[str, Any]]) -> str:
        """Use the configured LLM to produce a short executive summary of discrepancies."""
        descriptions = "\n\n".join([f"- {it.get('description', '')}" for it in items])
        prompt_text = (
            "You are an experienced infra analyst. Provide a crisp and brief executive summary of the following discrepancies "
            "using ONLY concise bullet points. Highlight key risk areas and recommended next steps:\n\n"
            f"{descriptions}"
        )

        if self.llm_provider == "gemini":
            if not self.gemini_client:
                raise RuntimeError("GEMINI_API_KEY is not set. Set it to use Gemini summarization.")
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"System: You are an experienced infrastructure analyst.\n\nUser: {prompt_text}"
                )
                return response.text.strip()
            except Exception:
                logging.exception("Gemini API call failed")
                raise

        if not self.openai_client:
            raise RuntimeError("OPENAI_API_KEY is not set. Set it to use LLM summarization.")
            
        try:
            resp = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an experienced infrastructure analyst."},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.0,
                max_tokens=500,
            )
            if hasattr(resp, "choices") and resp.choices:
                choice = resp.choices[0]
                if hasattr(choice, "message"):
                    return choice.message.get("content", "").strip()
                return choice.get("message", {}).get("content", "").strip()
            return getattr(resp, "output_text", "").strip()
        except Exception:
            logging.exception("OpenAI ChatCompletion failed")
            raise


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    sample = [
        {"id": "d1", "description": "Host SRV-002 hostname drifted to web-prod-01.local"},
        {"id": "d2", "description": "SRV-003 RAM reported as 16384 MB (16 GB) but CMDB lists 8 GB"},
    ]

    agent = AgentLLM()
    agent.index_discrepancies(sample)
    try:
        s = agent.summarize_discrepancies(sample)
        print("SUMMARY:\n", s)
    except RuntimeError as e:
        print("LLM unavailable:", e)
