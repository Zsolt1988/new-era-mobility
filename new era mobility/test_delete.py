import urllib.request
import json

with open('sold_archive.json', 'r') as f:
    data = json.load(f)
print("Before:", len(data))

# Find ID '1'
car_to_delete = None
for c in data:
    if c['id'] == '1':
        car_to_delete = c
        break

if car_to_delete:
    req = urllib.request.Request('http://localhost:8085/api/delete-car', data=json.dumps({'id': '1'}).encode('utf-8'), headers={'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req)
    print("Delete response:", response.read().decode('utf-8'))
    
    # Restore it
    data.append(car_to_delete)
    with open('sold_archive.json', 'w') as f:
        json.dump(data, f, indent=4)
