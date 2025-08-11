-- Flask-AppBuilder Apache AGE Graph Analytics Platform
-- Database Initialization Script
-- 
-- This script initializes the PostgreSQL database with Apache AGE extension
-- and creates the necessary schemas, indexes, and initial data structures.

-- Enable Apache AGE extension
CREATE EXTENSION IF NOT EXISTS age;

-- Load the AGE extension
LOAD 'age';

-- Set search path to include AGE catalog
SET search_path = ag_catalog, "$user", public;

-- Create initial analytics graph
SELECT create_graph('analytics_graph');

-- Create sample graphs for different use cases
SELECT create_graph('social_network');
SELECT create_graph('knowledge_graph');
SELECT create_graph('process_flow');
SELECT create_graph('infrastructure');

-- Grant permissions to the graph admin user
GRANT USAGE ON SCHEMA ag_catalog TO graph_admin;
GRANT ALL ON ALL TABLES IN SCHEMA ag_catalog TO graph_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA ag_catalog TO graph_admin;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA ag_catalog TO graph_admin;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_ag_label_vertex_id ON ag_catalog.ag_label USING btree (id);
CREATE INDEX IF NOT EXISTS idx_ag_label_edge_id ON ag_catalog.ag_label USING btree (id);
CREATE INDEX IF NOT EXISTS idx_ag_label_vertex_props ON ag_catalog._ag_label_vertex USING gin (properties);
CREATE INDEX IF NOT EXISTS idx_ag_label_edge_props ON ag_catalog._ag_label_edge USING gin (properties);

-- Create custom functions for graph analytics
CREATE OR REPLACE FUNCTION get_graph_stats(graph_name text)
RETURNS TABLE(
    node_count bigint,
    edge_count bigint,
    avg_degree numeric,
    density numeric
) AS $$
DECLARE
    node_cnt bigint;
    edge_cnt bigint;
    avg_deg numeric;
    graph_density numeric;
BEGIN
    -- Count nodes
    EXECUTE format('SELECT count(*) FROM cypher(%L, $$ MATCH (n) RETURN count(n) $$) as (count agtype)', graph_name)
    INTO node_cnt;
    
    -- Count edges
    EXECUTE format('SELECT count(*) FROM cypher(%L, $$ MATCH ()-[r]->() RETURN count(r) $$) as (count agtype)', graph_name)
    INTO edge_cnt;
    
    -- Calculate average degree
    IF node_cnt > 0 THEN
        avg_deg := (edge_cnt * 2.0) / node_cnt;
    ELSE
        avg_deg := 0;
    END IF;
    
    -- Calculate density
    IF node_cnt > 1 THEN
        graph_density := (edge_cnt * 2.0) / (node_cnt * (node_cnt - 1));
    ELSE
        graph_density := 0;
    END IF;
    
    RETURN QUERY SELECT node_cnt, edge_cnt, avg_deg, graph_density;
END;
$$ LANGUAGE plpgsql;

-- Create function for graph cleanup
CREATE OR REPLACE FUNCTION cleanup_orphaned_nodes(graph_name text)
RETURNS bigint AS $$
DECLARE
    deleted_count bigint;
BEGIN
    EXECUTE format('
        SELECT count(*) FROM cypher(%L, $$
            MATCH (n)
            WHERE NOT (n)-[]-()
            DELETE n
            RETURN count(n)
        $$) as (count agtype)', graph_name)
    INTO deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for graph metrics (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS graph_metrics AS
SELECT 
    graph_name,
    (get_graph_stats(graph_name)).node_count,
    (get_graph_stats(graph_name)).edge_count,
    (get_graph_stats(graph_name)).avg_degree,
    (get_graph_stats(graph_name)).density,
    NOW() as last_updated
FROM (
    SELECT DISTINCT graph_name 
    FROM ag_catalog.ag_graph
) graphs;

-- Create index on the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_graph_metrics_name ON graph_metrics (graph_name);

-- Grant permissions on custom objects
GRANT ALL ON graph_metrics TO graph_admin;
GRANT EXECUTE ON FUNCTION get_graph_stats(text) TO graph_admin;
GRANT EXECUTE ON FUNCTION cleanup_orphaned_nodes(text) TO graph_admin;

-- Create trigger to refresh metrics periodically
CREATE OR REPLACE FUNCTION refresh_graph_metrics()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY graph_metrics;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
DO $$ 
BEGIN 
    RAISE NOTICE 'Apache AGE initialization completed successfully!';
    RAISE NOTICE 'Created graphs: analytics_graph, social_network, knowledge_graph, process_flow, infrastructure';
    RAISE NOTICE 'Created custom functions: get_graph_stats, cleanup_orphaned_nodes';
    RAISE NOTICE 'Created materialized view: graph_metrics';
END $$;