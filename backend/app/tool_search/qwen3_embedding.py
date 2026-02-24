# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sentence_transformers import SentenceTransformer
import numpy as np
import torch
from typing import List, Dict
import logging
import threading
from enum import Enum
logger = logging.getLogger(__name__)

class NormalizationType(Enum):
    #MEAN_P = "mean_pooling"
    NONE = "NONE"
    L1 = "L1"
    L2 = "L2"


class SimilarityType(Enum):
    COSINE = "COSINE"  # Cosine similarity, COSINE=L2_norm(IP)
    L2 = "L2"  # Euclidean distance
    IP = "IP"  # Inner product


class Qwen3Embedding:
    EB_NAME = "qwen3-embedding"
    MAX_CONTEXT_LENGTH = 32 * 1000

    def __init__(self, model_path: str, device: str = "cuda"):
        self.device = device
        default_model_name = "Qwen/Qwen3-Embedding-0.6B"
        self.model = SentenceTransformer(model_path if model_path else default_model_name, device=device)
        self.tokenizer = self.model.tokenizer
        self.locker = threading.Lock()

    def preprocess_text(self, text: str | List[str]) -> np.ndarray | torch.Tensor | Dict[str, torch.Tensor]:
        if isinstance(text, str):
            text = [text]
        #tokens_list = [self.tokenizer.encode(t) for t in text]
        #return np.stack(tokens_list)
        token_map, is_overflow = self.text_tokenize(text)
        logger.info(f"preprocess text for text embedding successfully,is_overflow:{is_overflow},text:{text}")
        return token_map

    def text_tokenize(self, text: List[str]) -> tuple[np.ndarray, bool]:
        token_map = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt')
        if token_map['input_ids'].shape[1] > self.MAX_CONTEXT_LENGTH:
            token_map['input_ids'] = token_map['input_ids'][:self.MAX_CONTEXT_LENGTH]
            token_map['attention_mask'] = token_map['attention_mask'][:self.MAX_CONTEXT_LENGTH]
            return token_map, True
        else:
            return token_map, False

    def batch_text_embedding(self,
                             tokens: List[np.ndarray | torch.Tensor] | np.ndarray | Dict[str, torch.Tensor],
                             norm_type: NormalizationType = NormalizationType.L2) -> List[np.ndarray]:
        if norm_type != NormalizationType.NONE:
            norm_p = 2 if norm_type == NormalizationType.L2 else 1

        if isinstance(tokens, list):
            if isinstance(tokens[0], torch.Tensor):
                tokens = [torch.numpy(t) for t in tokens]

            tokens = torch.stack(tokens)
        elif isinstance(tokens, torch.Tensor):
            tokens = torch.numpy(tokens)
        '''
        norm_val = (embeddings[i, ...].norm(dim=-1, keepdim=True, p=norm_p) if norm_type != NormalizationType.NONE else 1.0
        TODO(lingyue.ly) transformer does not support batched forward,should replace vllm to transformers later
        '''
        if isinstance(tokens, np.ndarray):
            embeddings = self._infer(tokens)
        elif isinstance(tokens, torch.Tensor):
            tokens = tokens.to(self.device)
            embeddings = self._infer(tokens)
        else:
            tensor_map = {key: tensor.to(self.device) for key, tensor in tokens.items()}
            embeddings = self._infer(**tensor_map)

        embedding_list = [(embeddings[i, ...] / (embeddings[i, ...].norm(dim=-1, keepdim=True, p=norm_p))
                           if norm_type != NormalizationType.NONE else 1.0).cpu().detach().numpy()
                          for i in range(embeddings.shape[0])]
        return embedding_list

    def batch_calculate_similarity(self,
                                   query_embedding_list: List[np.ndarray],
                                   document_embedding_list: List[np.ndarray] | np.ndarray,
                                   similarity_type: SimilarityType = SimilarityType.IP) -> np.ndarray:
        '''
        Args:
            query_embedding_list: List[np.ndarray] (N, D)
            document_embedding_list: List[np.ndarray] (M, D)
            similarity_type: SimilarityType,default type is COSINE,so the similarity type is COSINE
        Returns:
            similarity_matrix: np.ndarray (N, M)
        '''
        query_embeddings = np.stack(query_embedding_list, axis=0)
        if isinstance(document_embedding_list, list):
            document_embeddings = np.stack(document_embedding_list, axis=0)
        else:
            document_embeddings = document_embedding_list
        if similarity_type == SimilarityType.IP:
            similarity_matrix = np.dot(query_embeddings, document_embeddings.T)
        elif similarity_type == SimilarityType.COSINE:
            similarity_matrix = np.dot(query_embeddings, document_embeddings.T) / (np.linalg.norm(
                query_embeddings, axis=-1, keepdim=True) * np.linalg.norm(document_embeddings, axis=-1, keepdim=True))
        elif similarity_type == SimilarityType.L2:
            similarity_matrix = np.zeros((query_embeddings.shape[0], document_embeddings.shape[0]), dtype=np.float32)
            for i, query_embedding in enumerate(query_embedding_list):
                for j, document_embedding in enumerate(document_embedding_list):
                    similarity_matrix[i, j] = np.linalg.norm(query_embedding - document_embedding, axis=-1, keepdim=True)
            return similarity_matrix
        else:
            raise ValueError(f"The similarity_type {similarity_type} is not supported!!")

        return similarity_matrix

    def _infer(self, *args, **kwargs):
        with self.locker:
            if kwargs is not None and "input_ids" in kwargs:
                with torch.no_grad():
                    model_output = self.model(input=kwargs)
                    embeddings = model_output['sentence_embedding']
                    return embeddings
            else:
                return self.model.encode(*args, **kwargs)
