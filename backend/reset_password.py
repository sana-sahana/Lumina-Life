from database.db import get_db
import hashlib

def check_user_password():
    db = get_db()
    
    email = "asifa@luminalife.com"
    user = db.users.find_one({"email": email})
    
    if user:
        stored_hash = user.get("password_hash", "")
        print(f"📧 User found: {email}")
        print(f"🔐 Stored password hash: {stored_hash}")
        print(f"📏 Hash length: {len(stored_hash)} characters")
        
        # Try to see if it's plain text
        if len(stored_hash) < 20:
            print(f"⚠️ Password appears to be plain text: '{stored_hash}'")
        elif len(stored_hash) == 64:
            print("✅ Password is SHA256 hash (64 chars)")
            
        # Test with common passwords
        test_passwords = ["password123", "asifa123", "admin123", "12345678"]
        print("\n🧪 Testing common passwords:")
        for test_pw in test_passwords:
            test_hash = hashlib.sha256(test_pw.encode()).hexdigest()
            if test_hash == stored_hash:
                print(f"   ✅ MATCH FOUND! Password is: '{test_pw}'")
                break
            else:
                print(f"   ❌ '{test_pw}' - No match")
    else:
        print(f"❌ User {email} not found")
        
        # List all users
        print("\n📋 All registered users:")
        users = db.users.find({}, {"email": 1, "user_id": 1})
        for u in users:
            print(f"   - {u.get('email')}")

if __name__ == "__main__":
    check_user_password()