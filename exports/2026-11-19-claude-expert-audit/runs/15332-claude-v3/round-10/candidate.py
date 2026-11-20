def compute_tp_gnn_loss(
    positive_scores,
    negative_scores,
    embeddings,
    positive_sources,
    positive_targets,
    negative_sources,
    negative_targets,
    source_batch_size,
    epoch,
    max_epochs,
    graph_scores,
    graph_sources,
    graph_targets,
    graph_net_ids,
    graph_weights,
    net_weights,
    node_features,
    node_areas,
):
    """Change vs parent: keep the sampled log-sigmoid contrastive term, and add a
    net-weight-normalized softplus margin on timing-star graph edges. The edge
    weights sum to each represented net's fixed timing weight, so timing-critical
    nets are attracted more strongly in the learned embedding geometry.

    Expected measurable effect: connected timing-critical supernodes become closer
    in L2 embedding space, moving the area-balanced two-means boundary and reducing
    the inter-die timing cut (especially TNS). The hypothesis is invalidated if the
    paired physical evaluation shows broad regression or mostly unchanged final
    assignments with no timing gain.
    """
    contrastive = -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)

    if len(graph_scores) > 0:
        edge_margin = F.softplus(0.5 - graph_scores)
        weighted_edges = edge_margin * graph_weights
        edge_norm = torch.clamp(graph_weights.sum(), min=1e-6)
        graph_penalty = 6.0 * weighted_edges.sum() / edge_norm
    else:
        graph_penalty = torch.zeros_like(contrastive)

    return contrastive + graph_penalty


def decode_tp_gnn_embeddings(embeddings, node_areas, seed, max_iterations, balance_target):
    """Unchanged from parent: call the frozen area-balanced global two-way helper
    exactly once with the supplied inputs. The protected feasibility closure still
    owns all area and macro repairs and recomputes centers from the returned labels.
    """
    return reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)
