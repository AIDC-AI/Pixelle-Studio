from typing import List, Dict, Any,Set
from pydantic import BaseModel, Field,field_validator,field_serializer,ConfigDict
import numpy as np


class ToolEmbeddingData(BaseModel):
    tool_name: str
    tool_description: str
    #embedding_data: List[float]


class EmbeddingDatas(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    embedding_datas: Dict[str, List[ToolEmbeddingData]] = Field(default_factory=dict)
    embeddings: np.ndarray | None = None
    embedding_indexs: List[str] = Field(default_factory=list)  #the md5 string of the string: "${mcp_server_name}||||${tool_name}".

    @field_validator("embeddings", mode="before")
    def validate_embeddings(cls, v: List[List[float]]) -> np.ndarray:
        np_embeddings = [np.array(item) for item in v]
        np_embedding = np.stack(np_embeddings)
        return np_embedding

    @field_serializer("embeddings")
    def serialize_embeddings(self, v: np.ndarray | None):
        assert len(v.shape) ==2,f"embeddings should be a 2D array,but got shape:{v.shape}"
        if v is None:
            return None
        embeddings_list = []
        for i in range(v.shape[0]):
            embeddings_list.append(v[i].tolist())
        return embeddings_list
            
        
