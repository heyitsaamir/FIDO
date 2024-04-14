from typing import List
from scipy import spatial

def distances_from_embeddings(
    query_embedding: List[float],
    embeddings: List[List[float]],
    distance_metric="cosine",
) -> List[float]:
    """Return the distances between a query embedding and a list of embeddings."""
    distance_metrics = {
        "cosine": spatial.distance.cosine,
        "L1": spatial.distance.cityblock,
        "L2": spatial.distance.euclidean,
        "Linf": spatial.distance.chebyshev,
    }
    distances = [
        distance_metrics[distance_metric](query_embedding, embedding)
        for embedding in embeddings
    ]
    return distances


def indices_of_nearest_neighbors_from_distances(distances: List[float], max_distance: float) -> List[int]:
    """Return a list of indices of nearest neighbors from a list of distances."""
    # Sort distances and get their indices
    sorted_indices = sorted(range(len(distances)), key=lambda i: distances[i])

    # Filter indices based on max_distance
    filtered_indices = [
        i for i in sorted_indices if distances[i] <= max_distance]

    return filtered_indices