from app.services.supabase.factory import get_supabase_client
from app.tools.appointments import get_available_slots, book_appointment

client = get_supabase_client()

# 1. Find a real doctor to test against (Harsh Sharma, in Orthopedics)
doctor = client.table('doctors').select('id, department_id').eq(
    'user_id', '04426c48-e57f-4b64-bb7b-27cfb520bc33'
).single().execute().data
print('doctor:', doctor)

# 2. Create a throwaway slot for him — this is real test data, gets deleted at the end
slot = client.table('appointment_slots').insert({
    'doctor_id': doctor['id'],
    'start_time': '2026-08-01T10:00:00+00:00',
    'end_time': '2026-08-01T10:30:00+00:00',
}).execute().data[0]
print('slot created:', slot)

# 3. Create a throwaway patient profile (reusing an existing login id, since the
#    FK requires a real profiles.id — who it "belongs to" doesn't matter for this test)
patient = client.table('patient_profiles').insert({
    'user_id': '5b962a3b-5497-4b5a-b460-1e7359654a8b'
}).execute().data[0]
print('patient created:', patient)

# 4. Check the slot shows up as available BEFORE booking
available_before = get_available_slots(doctor['department_id'])
print('available before booking:', [s['id'] for s in available_before])

# 5. Actually call the function being tested
booked = book_appointment(patient['id'], slot['id'], doctor['department_id'], 'knee pain follow-up')
print('booked appointment:', booked)

# 6. Check the slot is GONE from available slots AFTER booking
available_after = get_available_slots(doctor['department_id'])
print('available after booking:', [s['id'] for s in available_after])

# 7. Double check the slot's own status flipped correctly
slot_status = client.table('appointment_slots').select('status').eq('id', slot['id']).single().execute().data
print('slot status after booking:', slot_status)

# 8. Clean up everything created in steps 2-3, in reverse order (appointment
#    references the slot and patient, so it has to go first)
client.table('appointments').delete().eq('id', booked['id']).execute()
client.table('appointment_slots').delete().eq('id', slot['id']).execute()
client.table('patient_profiles').delete().eq('id', patient['id']).execute()
print('cleaned up')
