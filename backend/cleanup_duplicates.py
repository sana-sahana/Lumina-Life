from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['lumina_life']

print("📊 Before cleanup:")
print(f"Donations: {db.donations.count_documents({})}")
print(f"Profile: {db.user_profiles.find_one({'user_id': 'D001'})}")

# Delete duplicate donations
result = db.donations.delete_many({
    'hospital_name': 'Manipal Hospital, Old Airport Road'
})
print(f"\n✅ Deleted {result.deleted_count} duplicate donations")

# Reset profile stats
update_result = db.user_profiles.update_one(
    {'user_id': 'D001'},
    {
        '$set': {
            'total_donations': 0,
            'lives_saved': 0,
            'last_donation_date': None
        }
    }
)
print(f"✅ Updated profile: {update_result.modified_count} fields modified")

# Delete duplicate notifications
notif_result = db.notifications.delete_many({
    'type': 'donation_completed',
    'message': {'$regex': 'Manipal Hospital, Old Airport Road'}
})
print(f"✅ Deleted {notif_result.deleted_count} duplicate notifications")

# Delete duplicate arrival notifications
arrival_result = db.notifications.delete_many({
    'type': 'arrival_confirmed',
    'message': {'$regex': 'Manipal Hospital, Old Airport Road'}
})
print(f"✅ Deleted {arrival_result.deleted_count} duplicate arrival notifications")

# Show results
print("\n📊 After cleanup:")
print(f"Donations: {db.donations.count_documents({})}")
profile = db.user_profiles.find_one({'user_id': 'D001'})
print(f"Profile: total_donations={profile.get('total_donations', 0)}, lives_saved={profile.get('lives_saved', 0)}")

# Show remaining donations
print("\n📋 Remaining donations:")
for d in db.donations.find({}, {'_id': 0, 'hospital_name': 1, 'created_at': 1}):
    print(f"  - {d.get('hospital_name')} at {d.get('created_at')}")

client.close()
print("\n✅ Cleanup complete!")