-- Flask-AppBuilder Apache AGE Graph Analytics Platform
-- Sample Data Initialization
-- 
-- This script creates sample data to demonstrate the platform's capabilities

-- Set search path
SET search_path = ag_catalog, "$user", public;

-- Sample data for social network graph
SELECT * FROM cypher('social_network', $$
    CREATE (alice:Person {name: 'Alice Johnson', age: 28, role: 'Data Scientist', department: 'Analytics'})
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    CREATE (bob:Person {name: 'Bob Smith', age: 32, role: 'Software Engineer', department: 'Engineering'})
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    CREATE (carol:Person {name: 'Carol Davis', age: 29, role: 'Product Manager', department: 'Product'})
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    CREATE (david:Person {name: 'David Wilson', age: 35, role: 'Team Lead', department: 'Engineering'})
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    CREATE (eve:Person {name: 'Eve Brown', age: 26, role: 'UX Designer', department: 'Design'})
$$) as (result agtype);

-- Create relationships in social network
SELECT * FROM cypher('social_network', $$
    MATCH (alice:Person {name: 'Alice Johnson'})
    MATCH (bob:Person {name: 'Bob Smith'})
    CREATE (alice)-[r:COLLABORATES_WITH {project: 'ML Pipeline', since: '2023-01-15'}]->(bob)
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    MATCH (bob:Person {name: 'Bob Smith'})
    MATCH (david:Person {name: 'David Wilson'})
    CREATE (bob)-[r:REPORTS_TO {since: '2022-06-01'}]->(david)
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    MATCH (carol:Person {name: 'Carol Davis'})
    MATCH (alice:Person {name: 'Alice Johnson'})
    CREATE (carol)-[r:WORKS_WITH {project: 'Analytics Dashboard', frequency: 'weekly'}]->(alice)
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    MATCH (eve:Person {name: 'Eve Brown'})
    MATCH (carol:Person {name: 'Carol Davis'})
    CREATE (eve)-[r:COLLABORATES_WITH {project: 'User Research', since: '2023-03-10'}]->(carol)
$$) as (result agtype);

SELECT * FROM cypher('social_network', $$
    MATCH (david:Person {name: 'David Wilson'})
    MATCH (carol:Person {name: 'Carol Davis'})
    CREATE (david)-[r:COORDINATES_WITH {meeting: 'bi-weekly', topic: 'product roadmap'}]->(carol)
$$) as (result agtype);

-- Sample data for knowledge graph
SELECT * FROM cypher('knowledge_graph', $$
    CREATE (ml:Topic {name: 'Machine Learning', category: 'Technology', complexity: 'Advanced'})
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    CREATE (python:Technology {name: 'Python', type: 'Programming Language', popularity: 'High'})
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    CREATE (sklearn:Library {name: 'Scikit-learn', language: 'Python', purpose: 'Machine Learning'})
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    CREATE (tensorflow:Framework {name: 'TensorFlow', company: 'Google', type: 'Deep Learning'})
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    CREATE (nlp:Topic {name: 'Natural Language Processing', category: 'AI', complexity: 'Advanced'})
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    CREATE (spacy:Library {name: 'spaCy', language: 'Python', purpose: 'NLP'})
$$) as (result agtype);

-- Create knowledge relationships
SELECT * FROM cypher('knowledge_graph', $$
    MATCH (ml:Topic {name: 'Machine Learning'})
    MATCH (python:Technology {name: 'Python'})
    CREATE (ml)-[r:IMPLEMENTED_WITH {strength: 'strong', popularity: 0.9}]->(python)
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    MATCH (sklearn:Library {name: 'Scikit-learn'})
    MATCH (python:Technology {name: 'Python'})
    CREATE (sklearn)-[r:BUILT_FOR]->(python)
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    MATCH (ml:Topic {name: 'Machine Learning'})
    MATCH (sklearn:Library {name: 'Scikit-learn'})
    CREATE (ml)-[r:USES_LIBRARY {type: 'primary'}]->(sklearn)
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    MATCH (nlp:Topic {name: 'Natural Language Processing'})
    MATCH (ml:Topic {name: 'Machine Learning'})
    CREATE (nlp)-[r:SUBFIELD_OF]->(ml)
$$) as (result agtype);

SELECT * FROM cypher('knowledge_graph', $$
    MATCH (nlp:Topic {name: 'Natural Language Processing'})
    MATCH (spacy:Library {name: 'spaCy'})
    CREATE (nlp)-[r:USES_LIBRARY {type: 'primary'}]->(spacy)
$$) as (result agtype);

-- Sample data for process flow graph
SELECT * FROM cypher('process_flow', $$
    CREATE (start:Process {name: 'Data Ingestion', type: 'Input', duration: 30})
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    CREATE (validate:Process {name: 'Data Validation', type: 'Processing', duration: 15})
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    CREATE (clean:Process {name: 'Data Cleaning', type: 'Processing', duration: 45})
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    CREATE (transform:Process {name: 'Data Transformation', type: 'Processing', duration: 60})
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    CREATE (analyze:Process {name: 'Data Analysis', type: 'Processing', duration: 90})
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    CREATE (report:Process {name: 'Report Generation', type: 'Output', duration: 20})
$$) as (result agtype);

-- Create process flow relationships
SELECT * FROM cypher('process_flow', $$
    MATCH (start:Process {name: 'Data Ingestion'})
    MATCH (validate:Process {name: 'Data Validation'})
    CREATE (start)-[r:FLOWS_TO {order: 1, condition: 'always'}]->(validate)
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    MATCH (validate:Process {name: 'Data Validation'})
    MATCH (clean:Process {name: 'Data Cleaning'})
    CREATE (validate)-[r:FLOWS_TO {order: 2, condition: 'if_valid'}]->(clean)
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    MATCH (clean:Process {name: 'Data Cleaning'})
    MATCH (transform:Process {name: 'Data Transformation'})
    CREATE (clean)-[r:FLOWS_TO {order: 3, condition: 'always'}]->(transform)
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    MATCH (transform:Process {name: 'Data Transformation'})
    MATCH (analyze:Process {name: 'Data Analysis'})
    CREATE (transform)-[r:FLOWS_TO {order: 4, condition: 'always'}]->(analyze)
$$) as (result agtype);

SELECT * FROM cypher('process_flow', $$
    MATCH (analyze:Process {name: 'Data Analysis'})
    MATCH (report:Process {name: 'Report Generation'})
    CREATE (analyze)-[r:FLOWS_TO {order: 5, condition: 'always'}]->(report)
$$) as (result agtype);

-- Sample data for infrastructure graph
SELECT * FROM cypher('infrastructure', $$
    CREATE (web:Server {name: 'web-server-01', type: 'Web Server', os: 'Ubuntu 20.04', cpu: 4, memory: 8})
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    CREATE (app:Server {name: 'app-server-01', type: 'Application Server', os: 'Ubuntu 20.04', cpu: 8, memory: 16})
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    CREATE (db:Server {name: 'db-server-01', type: 'Database Server', os: 'Ubuntu 20.04', cpu: 16, memory: 32})
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    CREATE (cache:Server {name: 'cache-server-01', type: 'Cache Server', os: 'Ubuntu 20.04', cpu: 4, memory: 16})
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    CREATE (lb:LoadBalancer {name: 'load-balancer-01', type: 'Load Balancer', algorithm: 'round-robin'})
$$) as (result agtype);

-- Create infrastructure relationships
SELECT * FROM cypher('infrastructure', $$
    MATCH (lb:LoadBalancer {name: 'load-balancer-01'})
    MATCH (web:Server {name: 'web-server-01'})
    CREATE (lb)-[r:ROUTES_TO {weight: 50, port: 80}]->(web)
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    MATCH (web:Server {name: 'web-server-01'})
    MATCH (app:Server {name: 'app-server-01'})
    CREATE (web)-[r:CONNECTS_TO {protocol: 'HTTP', port: 8080}]->(app)
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    MATCH (app:Server {name: 'app-server-01'})
    MATCH (db:Server {name: 'db-server-01'})
    CREATE (app)-[r:CONNECTS_TO {protocol: 'PostgreSQL', port: 5432}]->(db)
$$) as (result agtype);

SELECT * FROM cypher('infrastructure', $$
    MATCH (app:Server {name: 'app-server-01'})
    MATCH (cache:Server {name: 'cache-server-01'})
    CREATE (app)-[r:CONNECTS_TO {protocol: 'Redis', port: 6379}]->(cache)
$$) as (result agtype);

-- Create some cross-graph relationships for demonstration
SELECT * FROM cypher('social_network', $$
    MATCH (alice:Person {name: 'Alice Johnson'})
    RETURN id(alice) as alice_id
$$) as (alice_id agtype);

-- Add some metrics and analytics data
SELECT * FROM cypher('analytics_graph', $$
    CREATE (metric1:Metric {
        name: 'User Engagement',
        value: 0.75,
        timestamp: '2023-12-01T10:00:00Z',
        source: 'web_analytics'
    })
$$) as (result agtype);

SELECT * FROM cypher('analytics_graph', $$
    CREATE (metric2:Metric {
        name: 'System Performance',
        value: 0.92,
        timestamp: '2023-12-01T10:00:00Z',
        source: 'monitoring'
    })
$$) as (result agtype);

SELECT * FROM cypher('analytics_graph', $$
    CREATE (event1:Event {
        type: 'user_login',
        timestamp: '2023-12-01T09:30:00Z',
        user_id: 'alice.johnson',
        session_id: 'sess_123456'
    })
$$) as (result agtype);

SELECT * FROM cypher('analytics_graph', $$
    CREATE (event2:Event {
        type: 'query_executed',
        timestamp: '2023-12-01T09:35:00Z',
        user_id: 'alice.johnson',
        query_type: 'graph_analysis',
        execution_time: 1.25
    })
$$) as (result agtype);

-- Refresh the materialized view to include sample data
REFRESH MATERIALIZED VIEW graph_metrics;

-- Log successful sample data creation
DO $$ 
BEGIN 
    RAISE NOTICE 'Sample data initialization completed successfully!';
    RAISE NOTICE 'Created sample data in: social_network, knowledge_graph, process_flow, infrastructure, analytics_graph';
    RAISE NOTICE 'Total nodes created: ~25 across all graphs';
    RAISE NOTICE 'Total relationships created: ~20 across all graphs';
    RAISE NOTICE 'Refreshed graph_metrics materialized view';
END $$;