-- GEO audit DuckDB schema
-- Schema version: 1.0.0
-- One process owns writes. The report skill opens a completed database read-only.

CREATE TABLE IF NOT EXISTS geo_schema_version (
    component VARCHAR PRIMARY KEY,
    version VARCHAR NOT NULL,
    applied_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_audit_runs (
    run_id VARCHAR PRIMARY KEY,
    revision BIGINT NOT NULL CHECK (revision >= 1),
    state VARCHAR NOT NULL CHECK (state IN (
        'CREATED', 'PREFLIGHT', 'WAITING_FOR_CONFIG', 'WAITING_FOR_INPUTS',
        'READY', 'READY_WITH_GAPS', 'COLLECTING', 'STAGED', 'CLUSTERING',
        'WAITING_FOR_CLUSTER_CONFIRMATION', 'ANALYZING', 'VALIDATING',
        'ANALYSIS_COMPLETE', 'ANALYSIS_COMPLETE_WITH_GAPS', 'BLOCKED', 'FAILED'
    )),
    client_id VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    domain VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    config_sha256 VARCHAR NOT NULL,
    crawl_universe_sha256 VARCHAR,
    source_catalog_version VARCHAR NOT NULL,
    factor_catalog_version VARCHAR NOT NULL,
    policy_version VARCHAR NOT NULL,
    policy_fingerprint VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE (client_id, config_sha256, revision)
);

CREATE TABLE IF NOT EXISTS geo_analysis_events (
    run_id VARCHAR NOT NULL,
    event_sequence BIGINT NOT NULL CHECK (event_sequence >= 1),
    state VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    event_payload JSON,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, event_sequence)
);

CREATE TABLE IF NOT EXISTS geo_source_manifest (
    run_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    artifact_id VARCHAR NOT NULL,
    transport VARCHAR NOT NULL,
    artifact_path_or_locator VARCHAR NOT NULL,
    artifact_sha256 VARCHAR NOT NULL,
    byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
    snapshot_at TIMESTAMP,
    date_range_start DATE,
    date_range_end DATE,
    scope_json JSON NOT NULL,
    schema_fingerprint VARCHAR NOT NULL,
    adapter_version BIGINT NOT NULL,
    record_count BIGINT NOT NULL CHECK (record_count >= 0),
    valid_empty BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, source_code, artifact_id)
);

CREATE TABLE IF NOT EXISTS geo_source_checks (
    run_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    check_id VARCHAR NOT NULL,
    access_status VARCHAR NOT NULL CHECK (access_status IN ('pass', 'fail', 'auth_required')),
    data_status VARCHAR NOT NULL CHECK (data_status IN ('present', 'missing', 'partial', 'malformed')),
    scope_status VARCHAR NOT NULL CHECK (scope_status IN ('match', 'mismatch', 'unknown')),
    freshness_status VARCHAR NOT NULL CHECK (freshness_status IN ('current', 'stale', 'unknown')),
    blocking BOOLEAN NOT NULL,
    affected_factor_ids JSON NOT NULL,
    action VARCHAR,
    details_json JSON,
    checked_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, source_code, check_id)
);

CREATE TABLE IF NOT EXISTS geo_schema_registry (
    run_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    schema_fingerprint VARCHAR NOT NULL,
    adapter_version BIGINT NOT NULL,
    normalized_fields_json JSON NOT NULL,
    source_headers_json JSON,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, source_code, schema_fingerprint)
);

CREATE TABLE IF NOT EXISTS geo_join_quality (
    run_id VARCHAR NOT NULL,
    left_source_code VARCHAR NOT NULL,
    right_source_code VARCHAR NOT NULL,
    join_name VARCHAR NOT NULL,
    join_method VARCHAR NOT NULL CHECK (join_method IN ('exact', 'normalized_exact', 'fuzzy', 'unresolved')),
    left_count BIGINT NOT NULL CHECK (left_count >= 0),
    right_count BIGINT NOT NULL CHECK (right_count >= 0),
    matched_count BIGINT NOT NULL CHECK (matched_count >= 0),
    ambiguous_count BIGINT NOT NULL CHECK (ambiguous_count >= 0),
    unmatched_count BIGINT NOT NULL CHECK (unmatched_count >= 0),
    confidence_cap VARCHAR CHECK (confidence_cap IS NULL OR confidence_cap IN ('medium', 'low', 'ND')),
    method_fingerprint VARCHAR NOT NULL,
    PRIMARY KEY (run_id, join_name)
);

CREATE TABLE IF NOT EXISTS geo_sf_urls (
    run_id VARCHAR NOT NULL,
    page_url VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    content_type VARCHAR,
    status_code BIGINT,
    indexability VARCHAR,
    indexability_status VARCHAR,
    canonical_url VARCHAR,
    robots_directives VARCHAR,
    crawl_depth BIGINT,
    inlink_count BIGINT,
    outlink_count BIGINT,
    response_time_ms DOUBLE,
    response_bytes BIGINT,
    title VARCHAR,
    meta_description VARCHAR,
    h1 VARCHAR,
    word_count BIGINT,
    content_hash VARCHAR,
    is_html BOOLEAN NOT NULL,
    source_record_json JSON,
    PRIMARY KEY (run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_html_raw (
    run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    artifact_id VARCHAR NOT NULL,
    html_sha256 VARCHAR NOT NULL,
    extracted_text_sha256 VARCHAR,
    extracted_fields_json JSON NOT NULL,
    body_artifact_path VARCHAR,
    fetched_at TIMESTAMP,
    PRIMARY KEY (run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_html_rendered (
    run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    artifact_id VARCHAR NOT NULL,
    html_sha256 VARCHAR NOT NULL,
    extracted_text_sha256 VARCHAR,
    extracted_fields_json JSON NOT NULL,
    body_artifact_path VARCHAR,
    rendered_at TIMESTAMP,
    PRIMARY KEY (run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_html_parity (
    run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    dimension VARCHAR NOT NULL,
    raw_value_sha256 VARCHAR,
    rendered_value_sha256 VARCHAR,
    comparison_status VARCHAR NOT NULL CHECK (comparison_status IN ('added', 'same', 'changed', 'removed', 'not_comparable')),
    affected BOOLEAN,
    metric_value DOUBLE,
    details_json JSON,
    method_version VARCHAR NOT NULL,
    PRIMARY KEY (run_id, normalized_page_url, dimension)
);

CREATE TABLE IF NOT EXISTS geo_psi_lab (
    run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    strategy VARCHAR NOT NULL CHECK (strategy IN ('mobile', 'desktop')),
    tested_at TIMESTAMP NOT NULL,
    final_url VARCHAR,
    performance_score DOUBLE,
    accessibility_score DOUBLE,
    best_practices_score DOUBLE,
    seo_score DOUBLE,
    fcp_ms DOUBLE,
    lcp_ms DOUBLE,
    speed_index_ms DOUBLE,
    tbt_ms DOUBLE,
    cls DOUBLE,
    lab_basis BOOLEAN NOT NULL DEFAULT TRUE,
    crux_context_json JSON,
    audits_json JSON,
    PRIMARY KEY (run_id, normalized_page_url, strategy)
);

CREATE TABLE IF NOT EXISTS geo_gsc_search_analytics (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    data_date DATE,
    query VARCHAR,
    page_url VARCHAR,
    country VARCHAR,
    device VARCHAR,
    search_appearance VARCHAR,
    clicks DOUBLE NOT NULL,
    impressions DOUBLE NOT NULL,
    ctr DOUBLE,
    position DOUBLE,
    dimensions_json JSON NOT NULL,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_gsc_url_inspection (
    run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    inspected_at TIMESTAMP NOT NULL,
    sample_role VARCHAR NOT NULL,
    inclusion_reason VARCHAR NOT NULL,
    verdict VARCHAR,
    coverage_state VARCHAR,
    indexing_state VARCHAR,
    robots_txt_state VARCHAR,
    page_fetch_state VARCHAR,
    google_canonical VARCHAR,
    user_canonical VARCHAR,
    last_crawl_time TIMESTAMP,
    response_json JSON,
    PRIMARY KEY (run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_gsc_gai (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    data_date DATE,
    page_url VARCHAR,
    country VARCHAR,
    device VARCHAR,
    impressions DOUBLE NOT NULL CHECK (impressions >= 0),
    dimensions_json JSON NOT NULL,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_ahrefs_backlinks (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    referring_url VARCHAR NOT NULL,
    referring_domain VARCHAR,
    target_url VARCHAR NOT NULL,
    anchor VARCHAR,
    link_attributes VARCHAR,
    authority_metrics_json JSON,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    source_record_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_ahrefs_refdomains (
    run_id VARCHAR NOT NULL,
    referring_domain VARCHAR NOT NULL,
    backlink_count BIGINT,
    dofollow_count BIGINT,
    authority_metrics_json JSON,
    first_seen TIMESTAMP,
    source_record_json JSON,
    PRIMARY KEY (run_id, referring_domain)
);

CREATE TABLE IF NOT EXISTS geo_ahrefs_broken (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    referring_url VARCHAR NOT NULL,
    target_url VARCHAR NOT NULL,
    anchor VARCHAR,
    target_status_code BIGINT,
    authority_metrics_json JSON,
    source_record_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_models (
    run_id VARCHAR NOT NULL,
    llm_model VARCHAR NOT NULL,
    llm_label VARCHAR NOT NULL,
    tracking_model BOOLEAN NOT NULL,
    request_artifact_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, llm_model, tracking_model)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_overview (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    domain VARCHAR NOT NULL,
    country VARCHAR,
    llm_model VARCHAR,
    visibility_scope VARCHAR NOT NULL,
    prompt_count BIGINT NOT NULL CHECK (prompt_count >= 0),
    response_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_competitors (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    competitor_brand VARCHAR NOT NULL,
    country VARCHAR,
    llm_model VARCHAR,
    metrics_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_prompts (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    domain VARCHAR,
    country VARCHAR,
    llm_model VARCHAR,
    prompt_text VARCHAR NOT NULL,
    answer_text VARCHAR,
    generated_at TIMESTAMP,
    response_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_prompt_counts (
    run_id VARCHAR NOT NULL,
    data_date DATE NOT NULL,
    country VARCHAR,
    llm_model VARCHAR,
    prompt_count BIGINT NOT NULL CHECK (prompt_count >= 0),
    scope_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (run_id, data_date, country, llm_model)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_sources (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    source_host VARCHAR,
    source_domain VARCHAR,
    source_url VARCHAR,
    amount DOUBLE,
    prompt_count BIGINT,
    country VARCHAR,
    llm_model VARCHAR,
    response_json JSON,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_sistrix_sentiment (
    run_id VARCHAR NOT NULL,
    row_id VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    platform VARCHAR,
    topic VARCHAR,
    praise_count BIGINT CHECK (praise_count IS NULL OR praise_count >= 0),
    criticism_count BIGINT CHECK (criticism_count IS NULL OR criticism_count >= 0),
    displayed_score DOUBLE,
    calculated_score DOUBLE,
    percentile DOUBLE,
    quote_text VARCHAR,
    source_url VARCHAR,
    source_type VARCHAR,
    evidence_locator VARCHAR NOT NULL,
    PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS geo_dejan_agents (
    run_id VARCHAR NOT NULL,
    agent_name VARCHAR NOT NULL,
    tested_at TIMESTAMP NOT NULL,
    robots_result VARCHAR,
    additional_blocking_result VARCHAR,
    result_status VARCHAR NOT NULL,
    evidence_locator VARCHAR NOT NULL,
    PRIMARY KEY (run_id, agent_name)
);

CREATE TABLE IF NOT EXISTS geo_cluster_runs (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    crawl_universe_sha256 VARCHAR NOT NULL,
    source_table VARCHAR NOT NULL,
    html_url_count BIGINT NOT NULL CHECK (html_url_count >= 1),
    unresolved_count BIGINT NOT NULL CHECK (unresolved_count >= 0),
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, cluster_run_id)
);

CREATE TABLE IF NOT EXISTS geo_url_clusters_vertical (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    vertical_cluster VARCHAR NOT NULL,
    PRIMARY KEY (run_id, cluster_run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_url_clusters_horizontal (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    structural_pattern VARCHAR NOT NULL,
    url_type VARCHAR NOT NULL,
    pattern_confirmation_status VARCHAR NOT NULL,
    semantic_label VARCHAR,
    business_criticality VARCHAR CHECK (business_criticality IS NULL OR business_criticality IN ('critical', 'high', 'medium', 'low')),
    PRIMARY KEY (run_id, cluster_run_id, normalized_page_url)
);

CREATE TABLE IF NOT EXISTS geo_url_prefix_clusters (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    cluster_id VARCHAR NOT NULL,
    normalized_prefix VARCHAR NOT NULL,
    depth BIGINT NOT NULL CHECK (depth >= 0),
    parent_cluster_id VARCHAR,
    crawl_universe_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (run_id, cluster_run_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS geo_url_cluster_memberships (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    normalized_page_url VARCHAR NOT NULL,
    cluster_id VARCHAR NOT NULL,
    crawl_universe_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (run_id, cluster_run_id, normalized_page_url, cluster_id)
);

CREATE TABLE IF NOT EXISTS geo_cluster_semantic_map (
    run_id VARCHAR NOT NULL,
    cluster_run_id VARCHAR NOT NULL,
    slug_value VARCHAR NOT NULL,
    structural_layers_seen_json JSON NOT NULL,
    canonical_group VARCHAR NOT NULL,
    classification_status VARCHAR NOT NULL,
    assignment_signal VARCHAR NOT NULL,
    notes VARCHAR,
    PRIMARY KEY (run_id, cluster_run_id, slug_value)
);

CREATE TABLE IF NOT EXISTS geo_cluster_label_mappings (
    domain VARCHAR NOT NULL,
    normalized_pattern VARCHAR NOT NULL,
    mapping_version BIGINT NOT NULL CHECK (mapping_version >= 1),
    semantic_label VARCHAR NOT NULL,
    business_criticality VARCHAR NOT NULL CHECK (business_criticality IN ('critical', 'high', 'medium', 'low')),
    confirmation_status VARCHAR NOT NULL CHECK (confirmation_status = 'confirmed'),
    confirmed_at TIMESTAMP NOT NULL,
    pattern_definition_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (domain, normalized_pattern, mapping_version)
);

CREATE TABLE IF NOT EXISTS geo_factor_results (
    run_id VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    applicability VARCHAR NOT NULL CHECK (applicability IN ('applicable', 'not_applicable')),
    measurement_status VARCHAR NOT NULL CHECK (measurement_status IN ('measured', 'partially_measured', 'not_determined', 'not_applicable', 'source_error')),
    scope_type VARCHAR NOT NULL CHECK (scope_type IN ('full', 'representative_sample', 'diagnostic_sample', 'source_corpus', 'snapshot')),
    coverage_rate DOUBLE NOT NULL CHECK (coverage_rate >= 0 AND coverage_rate <= 1),
    confidence VARCHAR NOT NULL CHECK (confidence IN ('high', 'medium', 'low', 'ND')),
    method_id VARCHAR NOT NULL,
    method_fingerprint VARCHAR NOT NULL,
    limitations_json JSON NOT NULL,
    PRIMARY KEY (run_id, factor_id)
);

CREATE TABLE IF NOT EXISTS geo_factor_metrics (
    run_id VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    metric_name VARCHAR NOT NULL,
    metric_type VARCHAR NOT NULL,
    number_value DOUBLE,
    integer_value BIGINT,
    boolean_value BOOLEAN,
    string_value VARCHAR,
    unit VARCHAR NOT NULL,
    numerator DOUBLE,
    denominator DOUBLE,
    calculation_fingerprint VARCHAR NOT NULL,
    PRIMARY KEY (run_id, factor_id, metric_name)
);

CREATE TABLE IF NOT EXISTS geo_factor_cluster_metrics (
    run_id VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    cluster_id VARCHAR NOT NULL,
    affected_count BIGINT NOT NULL CHECK (affected_count >= 0),
    analyzed_count BIGINT NOT NULL CHECK (analyzed_count >= 0),
    affected_rate DOUBLE CHECK (affected_rate IS NULL OR (affected_rate >= 0 AND affected_rate <= 1)),
    applicable_universe_count BIGINT NOT NULL CHECK (applicable_universe_count >= 0),
    coverage_rate DOUBLE NOT NULL CHECK (coverage_rate >= 0 AND coverage_rate <= 1),
    crawl_universe_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (run_id, factor_id, cluster_id),
    CHECK (affected_count <= analyzed_count),
    CHECK (analyzed_count <= applicable_universe_count)
);

CREATE TABLE IF NOT EXISTS geo_evidence_drafts (
    run_id VARCHAR NOT NULL,
    evidence_uuid VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    artifact_id VARCHAR NOT NULL,
    artifact_sha256 VARCHAR NOT NULL,
    locator VARCHAR NOT NULL,
    method_id VARCHAR NOT NULL,
    method_fingerprint VARCHAR NOT NULL,
    grain VARCHAR NOT NULL,
    numerator DOUBLE,
    denominator DOUBLE,
    observed_value_json JSON NOT NULL,
    affected_clusters_json JSON,
    examples_json JSON,
    confidence VARCHAR NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    limitations_json JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, evidence_uuid)
);

CREATE TABLE IF NOT EXISTS geo_evidence (
    run_id VARCHAR NOT NULL,
    evidence_id VARCHAR NOT NULL,
    evidence_uuid VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    source_code VARCHAR NOT NULL,
    artifact_id VARCHAR NOT NULL,
    artifact_sha256 VARCHAR NOT NULL,
    locator VARCHAR NOT NULL,
    method_id VARCHAR NOT NULL,
    method_fingerprint VARCHAR NOT NULL,
    grain VARCHAR NOT NULL,
    numerator DOUBLE,
    denominator DOUBLE,
    observed_value_json JSON NOT NULL,
    affected_clusters_json JSON,
    examples_json JSON,
    confidence VARCHAR NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    limitations_json JSON NOT NULL,
    finalized_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, evidence_id),
    UNIQUE (run_id, evidence_uuid),
    CHECK (numerator IS NULL OR denominator IS NULL OR numerator <= denominator)
);

CREATE TABLE IF NOT EXISTS geo_findings (
    run_id VARCHAR NOT NULL,
    finding_id VARCHAR NOT NULL,
    factor_id VARCHAR NOT NULL,
    root_cause_group VARCHAR NOT NULL,
    statement VARCHAR NOT NULL,
    evidence_ids_json JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, finding_id)
);

CREATE TABLE IF NOT EXISTS geo_recommendation_candidates (
    run_id VARCHAR NOT NULL,
    recommendation_id VARCHAR NOT NULL,
    root_cause_key VARCHAR NOT NULL,
    factor_ids_json JSON NOT NULL,
    problem VARCHAR NOT NULL,
    why_important VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    expected_effect VARCHAR NOT NULL,
    effort VARCHAR NOT NULL CHECK (effort IN ('low', 'medium', 'high')),
    risk VARCHAR NOT NULL CHECK (risk IN ('low', 'medium', 'high')),
    validation_method VARCHAR NOT NULL,
    evidence_ids_json JSON NOT NULL,
    PRIMARY KEY (run_id, recommendation_id),
    UNIQUE (run_id, root_cause_key)
);

CREATE TABLE IF NOT EXISTS geo_analysis_limitations (
    run_id VARCHAR NOT NULL,
    limitation_id VARCHAR NOT NULL,
    scope_type VARCHAR NOT NULL,
    factor_ids_json JSON,
    statement VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, limitation_id)
);
