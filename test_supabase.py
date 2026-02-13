"""
Test script to verify Supabase connection and database operations
"""
from dbHandler import insertData, retrieveData

def test_insert():
    """Test inserting data into Supabase"""
    print("=" * 50)
    print("Testing INSERT operation...")
    print("=" * 50)
    
    test_data = {
        "Name": "test_criminal",
        "Father's Name": "test_father",
        "Mother's Name": "test_mother",
        "Gender": "male",
        "DOB(yyyy-mm-dd)": "1990-01-01",
        "Blood Group": "O+",
        "Identification Mark": "scar on left cheek",
        "Nationality": "test",
        "Religion": "test",
        "Crimes Done": "test crime"
    }
    
    row_id = insertData(test_data)
    
    if row_id > 0:
        print(f"✅ INSERT successful! Row ID: {row_id}")
        return row_id
    else:
        print("❌ INSERT failed!")
        return None

def test_retrieve():
    """Test retrieving data from Supabase"""
    print("\n" + "=" * 50)
    print("Testing RETRIEVE operation...")
    print("=" * 50)
    
    id, data = retrieveData("test_criminal")
    
    if id is not None and data is not None:
        print(f"✅ RETRIEVE successful!")
        print(f"   ID: {id}")
        print(f"   Name: {data['Name']}")
        print(f"   Gender: {data['Gender']}")
        return True
    else:
        print("❌ RETRIEVE failed!")
        return False

if __name__ == "__main__":
    print("\n🔍 Testing Supabase Connection...\n")
    
    # Test insert
    row_id = test_insert()
    
    if row_id:
        # Test retrieve
        success = test_retrieve()
        
        if success:
            print("\n" + "=" * 50)
            print("✅ All tests passed! Supabase migration is working correctly.")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("⚠️  Insert worked but retrieve failed. Check the code.")
            print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ Insert failed. Check your Supabase configuration.")
        print("=" * 50)

