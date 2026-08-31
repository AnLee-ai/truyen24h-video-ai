from src import database
client = database.get_client()
res = client.table('chapters').select('id, title, content').execute()
count = 0
for row in res.data:
    title = row.get('title', '')
    content = row.get('content', '')
    
    needs_update = False
    update_data = {}
    
    if 'Ã' in title or 'Æ' in title:
        try:
            update_data['title'] = title.encode('cp1252').decode('utf-8')
            needs_update = True
        except:
            pass
            
    if 'Ã' in content or 'Æ' in content:
        try:
            update_data['content'] = content.encode('cp1252').decode('utf-8')
            needs_update = True
        except:
            pass
            
    if needs_update:
        try:
            client.table('chapters').update(update_data).eq('id', row['id']).execute()
            count += 1
        except Exception as e:
            pass
            
print(f'Fixed {count} corrupted rows in Supabase')
