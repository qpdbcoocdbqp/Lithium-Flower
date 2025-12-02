import pymongo
import sys

def main():
    try:
        # 1. Connect
        client = pymongo.MongoClient("mongodb://localhost:27017/", directConnection=True)
        
        # Check connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully!")

        # List all databases
        db_names = client.list_database_names()
        print(f"📂 Available Databases: {db_names}")
        if "agentlightning" in db_names:
            db = client["agentlightning"]
            collections = db.list_collection_names()
            print(f"📂 Collections in 'agentlightning': {collections}")
            if len(collections) > 0:
                for collection_name in collections:
                    db[collection_name].delete_many({})
                    print(f"   Start cleaning collection: {collection_name}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main()
