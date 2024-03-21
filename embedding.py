import os

import openai

from dotenv import load_dotenv
from typing import List
from utils import distances_from_embeddings, indices_of_nearest_neighbors_from_distances

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def recommendations_from_strings(
    existing_objective_embeddings: List[List[float]],
    incoming_objective: str,
) -> int | None:
    """Return nearest neighbors of a given string."""
    embedding_for_incoming_objective = get_embedding(incoming_objective)

    # get distances between the source embedding and other embeddings (function from embeddings_utils.py)
    distances = distances_from_embeddings(
        embedding_for_incoming_objective, existing_objective_embeddings, distance_metric="cosine")

    # get indices of nearest neighbors (function from embeddings_utils.py)
    indices_of_nearest_neighbors = indices_of_nearest_neighbors_from_distances(
        distances, 0.5)
    return indices_of_nearest_neighbors[0] if indices_of_nearest_neighbors else None


def get_embedding(str: str):
    embedding = openai.embeddings.create(
        input=str,
        model="text-embedding-3-small",
    )
    return embedding.data[0].embedding
