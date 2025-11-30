import pymongo
import sys

def test_crud():
    try:
        # 1. Connect
        client = pymongo.MongoClient("mongodb://localhost:27017/", directConnection=True)
        
        # Check connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully!")
        
        db = client["test_db"]
        collection = db["test_collection"]
        
        # Clean up previous test data
        collection.drop()
        
        # 2. Create
        document = {"name": "Antigravity", "type": "AI", "status": "active"}
        result = collection.insert_one(document)
        print(f"✅ Created document with ID: {result.inserted_id}")
        
        # 3. Read
        found_doc = collection.find_one({"_id": result.inserted_id})
        print(f"✅ Read document: {found_doc}")
        
        if not found_doc or found_doc["name"] != "Antigravity":
            print("❌ Read failed or data mismatch")
            return

        # 4. Update
        update_result = collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "upgraded"}}
        )
        print(f"✅ Updated {update_result.modified_count} document(s)")
        
        updated_doc = collection.find_one({"_id": result.inserted_id})
        print(f"   New state: {updated_doc}")
        
        if updated_doc["status"] != "upgraded":
             print("❌ Update failed")
             return

        # 5. Delete
        delete_result = collection.delete_one({"_id": result.inserted_id})
        print(f"✅ Deleted {delete_result.deleted_count} document(s)")
        
        final_check = collection.find_one({"_id": result.inserted_id})
        if final_check is None:
            print("✅ Verify Delete: Document is gone")
        else:
            print("❌ Delete failed, document still exists")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    test_crud()
