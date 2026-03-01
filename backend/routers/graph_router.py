from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/graph/{student_id}")
async def get_graph(student_id: str):
    from main import get_neo4j_service
    from services import student_service

    neo4j = get_neo4j_service()
    profile = await student_service.get_profile(student_id)

    gap_ids = []
    mastered_ids = []
    decaying_ids = []

    if profile:
        gap_ids = [g.concept_id for g in profile.gap_areas]

        from services.decay_service import get_decaying_concepts
        decaying = get_decaying_concepts(profile)
        decaying_ids = [d["concept_id"] for d in decaying]

        for cid, score in profile.diagnostic_results.items():
            if score >= 0.6 and cid not in gap_ids:
                mastered_ids.append(cid)

    viz_data = await neo4j.get_visualization_data(gap_ids)

    for node in viz_data["nodes"]:
        if node["id"] in gap_ids:
            node["state"] = "gap"
        elif node["id"] in decaying_ids:
            node["state"] = "decaying"
        elif node["id"] in mastered_ids:
            node["state"] = "mastered"
        else:
            node["state"] = "unassessed"

    if profile:
        root_chains = {}
        for gap in profile.gap_areas:
            if gap.root_cause_chain:
                root_chains[gap.concept_id] = gap.root_cause_chain

        for node in viz_data["nodes"]:
            for gap_id, chain in root_chains.items():
                if node["id"] == chain[-1] and len(chain) > 1:
                    node["state"] = "root_cause"

        viz_data["root_cause_chains"] = root_chains

    return viz_data


@router.get("/graph/concept/{concept_id}")
async def get_concept_detail(concept_id: str):
    from main import get_neo4j_service

    neo4j = get_neo4j_service()
    concept = await neo4j.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept not found: {concept_id}")

    prereqs = await neo4j.get_prerequisites(concept_id, depth=3)
    dependents = await neo4j.count_dependents(concept_id)

    return {
        "concept": concept.model_dump(),
        "prerequisites": [p.model_dump() for p in prereqs],
        "dependent_count": dependents,
    }
