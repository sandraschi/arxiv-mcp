# arxiv-mcp (MCPB Bundle)

FastMCP 3.2.0 arXiv research server with LanceDB RAG and deep epistemic profiling

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "arxiv_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **api_logs**: api_logs
- **api_logs_push**: api_logs_push
- **api_llm_settings_get**: api_llm_settings_get
- **api_llm_settings_save**: api_llm_settings_save
- **health**: health
- **api_stats**: api_stats
- **api_categories**: api_categories
- **api_search**: api_search
- **api_preprints_search**: api_preprints_search
- **api_category_latest**: api_category_latest
- **api_search_advanced**: api_search_advanced
- **api_paper**: api_paper
- **api_corpus**: api_corpus
- **api_corpus_item**: api_corpus_item
- **api_depot_search**: api_depot_search
- **api_depot_rag_status**: api_depot_rag_status
- **api_depot_rag_reindex**: api_depot_rag_reindex
- **api_firefront_scan**: api_firefront_scan
- **api_codehunt_scan**: api_codehunt_scan
- **api_codehunt_repoll**: api_codehunt_repoll
- **api_codehunt_stats**: api_codehunt_stats
- **api_codehunt_media_check**: api_codehunt_media_check
- **api_pipeline_liveness**: api_pipeline_liveness
- **api_readly_settings**: api_readly_settings
- **api_publication_subscriptions**: api_publication_subscriptions
- **api_media_settings_get**: api_media_settings_get
- **api_media_settings_patch**: api_media_settings_patch
- **api_help_index**: api_help_index
- **api_help_topic**: api_help_topic
- **api_depot_ingest**: api_depot_ingest
- **api_depot_ingest_analyze**: api_depot_ingest_analyze
- **api_depot_analyze**: api_depot_analyze
- **api_depot_deep_analyze**: api_depot_deep_analyze
- **api_depot_epistemics_filter**: api_depot_epistemics_filter
- **api_calibre_ingest**: api_calibre_ingest
- **api_favorites_list**: api_favorites_list
- **api_favorites_add**: api_favorites_add
- **api_favorites_remove**: api_favorites_remove
- **api_tools**: api_tools
- **api_capabilities**: api_capabilities
- **api_skills**: api_skills
- **api_llm_discover**: api_llm_discover
- **api_lab_sources**: api_lab_sources
- **api_lab_posts**: api_lab_posts
- **api_lab_fetch**: api_lab_fetch
- **api_anthropic_posts**: api_anthropic_posts
- **api_anthropic_fetch**: api_anthropic_fetch
- **api_prompts**: api_prompts
- **api_fleet**: api_fleet
- **api_diagnostics**: api_diagnostics
- **root**: root
- **well_known_mcp_manifest**: well_known_mcp_manifest
- **search_papers**: search_papers
- **get_paper_details**: get_paper_details
- **fetch_full_text**: fetch_full_text
- **list_category_latest**: list_category_latest
- **find_connected_papers**: find_connected_papers
- **ingest_paper_to_corpus**: ingest_paper_to_corpus
- **analyze_paper_epistemics**: analyze_paper_epistemics
- **ingest_and_analyze_paper**: ingest_and_analyze_paper
- **deep_analyze_paper_epistemics**: deep_analyze_paper_epistemics
- **epistemic_job**: epistemic_job
- **list_depot_by_epistemics**: list_depot_by_epistemics
- **check_benchmark_claim**: check_benchmark_claim
- **search_depot_corpus**: search_depot_corpus
- **depot_rag_status**: depot_rag_status
- **reindex_depot_vectors**: reindex_depot_vectors
- **store_paper_to_calibre**: store_paper_to_calibre
- **compare_papers_convergence**: compare_papers_convergence
- **search**: search
- **search_advanced**: search_advanced
- **get_paper**: get_paper
- **get_content**: get_content
- **get_recent**: get_recent
- **list_categories**: list_categories
- **resolve_doi**: resolve_doi
- **fetch_doi_content**: fetch_doi_content
- **arxiv_agentic_assist**: arxiv_agentic_assist
- **arxiv_sampling_hint**: arxiv_sampling_hint
- **fetch_lab_post**: fetch_lab_post
- **list_lab_posts**: list_lab_posts
- **fetch_wikipedia_summary**: fetch_wikipedia_summary
- **search_wikipedia**: search_wikipedia
- **fetch_wikipedia_sections**: fetch_wikipedia_sections
- **fetch_anthropic_post**: fetch_anthropic_post
- **list_anthropic_posts**: list_anthropic_posts
- **check_invisible_text**: check_invisible_text
- **_arxiv_api_error_response_relevance**: _arxiv_api_error_response(relevance)
- **_arxiv_api_error_response_submitted**: _arxiv_api_error_response(submitted)
- **_arxiv_api_error_response_updated**: _arxiv_api_error_response(updated)
- **searchAdvanced**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **getPaper**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **getContent**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **getRecent**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **listCategories**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **run_firefront_scan_tool**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **show_paper_card**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **show_depot_rag_status_card**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **show_depot_stats_card**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **show_citation_graph_card**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **show_epistemic_profile_card**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **research_workflow_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **generate_summary_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **consciousness_survey_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **ai_consciousness_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **neurophilosophy_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **convergence_analysis_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **firefront_scan_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **corpus_build_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **replication_audit_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **epistemic_profile_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **citation_map_prompt**: arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.
- **run_codehunt_scan_tool**: run_codehunt_scan_tool
- **repoll_codehunt_tool**: repoll_codehunt_tool
- **codehunt_stats_tool**: codehunt_stats_tool
- **check_codehunt_media_tool**: check_codehunt_media_tool
- **pipeline_liveness_tool**: pipeline_liveness_tool
- **query_logs**: query_logs
- **arxiv_help**: arxiv_help
- **_truncate**: _truncate

## Requirements

- Python 3.12+
- uv
