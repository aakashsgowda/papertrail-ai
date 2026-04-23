"""
Script to clear all data from Neo4j database
"""
from dotenv import load_dotenv
load_dotenv()

from app.neo4j_db import get_driver, close_driver

def clear_all_data():
    drv = get_driver()
    with drv.session() as s:
        print("Deleting all nodes and relationships...")
        s.run("MATCH (n) DETACH DELETE n")
        print("✓ All data cleared!")
    close_driver()

if __name__ == "__main__":
    response = input("This will delete ALL data from your Neo4j database. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        clear_all_data()
        print("\nNow restart your server and upload your PDFs again.")
    else:
        print("Operation cancelled.")
