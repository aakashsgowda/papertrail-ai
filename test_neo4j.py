from dotenv import load_dotenv
load_dotenv()

from neo4j import GraphDatabase
from app.config import settings

try:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_lifetime=3600
    )
    with driver.session() as session:
        result = session.run("RETURN 1 as test")
        print("✓ Neo4j connection successful!")
        print(f"Test result: {result.single()['test']}")
    driver.close()
except Exception as e:
    print(f"✗ Neo4j connection failed: {e}")
