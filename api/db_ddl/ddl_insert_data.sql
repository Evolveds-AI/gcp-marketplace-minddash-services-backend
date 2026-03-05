
-- =======================================================
-- Cuerpo de mensaje para el agente
-- =======================================================


INSERT INTO public.clients_products_deploys (
    product_id,
    bucket_config,
    gs_examples_agent,
    gs_prompt_agent,
    gs_prompt_sql,
    gs_profiling_agent,
    gs_metrics_config_agent,
    client,
    "updated_at"
)
VALUES (
    '82c9669b-7ad4-429f-a52f-8985a7b279e2', -- Reemplaza con un ID de producto válido
    'gs-minddash-agent-env',
    'examples_agents/few_shot_examples.yaml',
    'prompts/prompts_agent_bayern.yaml',
    'prompts/query_exec_prompt.yaml',
    'profiling/metrics_data_bayern.yaml',
    'profiling/metrics_data_bayern.yaml',
    'postgresql_conn_bayer',
    CURRENT_TIMESTAMP
);


INSERT INTO public.clients_products_deploys (
    product_id,
    bucket_config,
    gs_examples_agent,
    gs_prompt_agent,
    gs_prompt_sql,
    gs_profiling_agent,
    gs_metrics_config_agent,
    client,
    "updated_at",
    gs_semantic_config
)
VALUES (
    '6a3de6f7-c878-41e5-a710-6e44881c5cef', -- Reemplaza con un ID de producto válido
    'gs-minddash-agent-env',
    'examples_agents/few_shot_example_demo.yaml',
    'prompts/agent_prompt_demo.yaml',
    'prompts/query_exec_prompt.yaml',
    '',
    '',
    'postgresql_conn_minddash_chatbot',
    CURRENT_TIMESTAMP,
    'semantic_layers/postgresql_conn_minddash_chatbot/03-11-2025.yaml'
);

