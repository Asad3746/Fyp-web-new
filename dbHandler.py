from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, TABLE_NAME

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insertData(data):
    """
    Insert criminal data into the database.
    
    Args:
    - data: Dictionary containing criminal data
    
    Returns:
    - ID of the inserted row
    """
    rowId = 0
    
    print("Connecting to Supabase...")
    
    # Get DOB value and handle empty strings (convert to None for PostgreSQL)
    dob_value = data.get("DOB(yyyy-mm-dd)", "")
    dob_value = None if dob_value == "" or dob_value is None else dob_value
    
    # Map the data dictionary keys to database column names
    insert_data = {
        "name": data.get("Name", ""),
        "father_name": data.get("Father's Name", ""),
        "mother_name": data.get("Mother's Name", ""),
        "gender": data.get("Gender", ""),
        "dob": dob_value,  # None if empty, otherwise the date string
        "blood_group": data.get("Blood Group", ""),
        "identification_mark": data.get("Identification Mark", ""),
        "nationality": data.get("Nationality", ""),
        "religion": data.get("Religion", ""),
        "crimes_done": data.get("Crimes Done", "")
    }
    
    try:
        response = supabase.table(TABLE_NAME).insert(insert_data).execute()
        if response.data:
            rowId = response.data[0]["id"]
            print("Data stored on row %d" % rowId)
        else:
            print("Data insertion failed: No data returned")
    except Exception as e:
        print("Data insertion failed: %s" % str(e))
    
    print("Connection closed")
    return rowId

def retrieveData(name):
    """
    Retrieve criminal data from the database based on the name.
    
    Args:
    - name: Name of the criminal
    
    Returns:
    - Tuple containing ID and criminal data
    """
    id = None
    criminaldata = None
    
    print("Connecting to Supabase...")
    
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("name", name.lower()).execute()
        
        if response.data and len(response.data) > 0:
            result = response.data[0]
            id = result["id"]
            criminaldata = {
                "Name": result.get("name", ""),
                "Father's Name": result.get("father_name", ""),
                "Mother's Name": result.get("mother_name", ""),
                "Gender": result.get("gender", ""),
                "DOB(yyyy-mm-dd)": result.get("dob", ""),
                "Blood Group": result.get("blood_group", ""),
                "Identification Mark": result.get("identification_mark", ""),
                "Nationality": result.get("nationality", ""),
                "Religion": result.get("religion", ""),
                "Crimes Done": result.get("crimes_done", "")
            }
            print("Data retrieved")
        else:
            print("No data found for name: %s" % name)
    except Exception as e:
        print("Error: Unable to fetch data - %s" % str(e))
    
    print("Connection closed")
    
    return id, criminaldata
