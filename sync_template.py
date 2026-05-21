import re

with open('index.html', 'r') as f:
    idx_content = f.read()

with open('create_html_table.py', 'r') as f:
    py_content = f.read()

# Extract the body content from index.html (everything from <body to </html>)
body_match = re.search(r'(<body.*</html>)', idx_content, re.DOTALL | re.IGNORECASE)
body_content = body_match.group(1)

# In the python f-string, { and } must be doubled to escape them, EXCEPT we don't want to mess up any python variables if there were any.
# Wait, the only python variable in the body template might be where `cars` array is. 
# But in index.html, the cars array is literal `const cars = [...];`.
# In create_html_table.py, the cars array is `const cars = {json.dumps(filtered_data)};`.
# So we need to do this carefully.

# Let's replace { and } with {{ and }}
escaped_body = body_content.replace('{', '{{').replace('}', '}}')

# Restore the json.dumps variable
escaped_body = re.sub(r'const cars = \[.*?\];;', 'const cars = {json.dumps(filtered_data)};', escaped_body, flags=re.DOTALL)
# Also fix the `;;` typo if any
escaped_body = re.sub(r'const cars = \[.*?\];', 'const cars = {json.dumps(filtered_data)};', escaped_body, flags=re.DOTALL)

# Now, we need to replace the corresponding part in create_html_table.py
# The html_template is an f-string. Let's find where <body starts.
py_parts = re.split(r'(<body.*</html>)', py_content, maxsplit=1, flags=re.DOTALL | re.IGNORECASE)

if len(py_parts) == 3:
    new_py_content = py_parts[0] + escaped_body + py_parts[2]
    with open('create_html_table.py', 'w') as f:
        f.write(new_py_content)
    print("Successfully synchronized create_html_table.py")
else:
    print("Could not find body tag in create_html_table.py")

