"""Debug text overflow: check word-wrap vs white-space conflicts."""
import sys
sys.path.insert(0, '.')
from bs4 import BeautifulSoup

with open('test_output.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"word-wrap count: {html.count('word-wrap')}")
print(f"overflow-wrap count: {html.count('overflow-wrap')}")
print(f"white-space nowrap count: {html.count('white-space: nowrap')}")

# Check if word-wrap is applied to containers with tables inside
soup = BeautifulSoup(html, 'html.parser')
divs_with_wordwrap = soup.find_all('div', style=lambda s: s and 'word-wrap' in s)
divs_with_tables = [d for d in divs_with_wordwrap if d.find('table')]
print(f"\nDivs with word-wrap: {len(divs_with_wordwrap)}")
print(f"Divs with word-wrap AND tables: {len(divs_with_tables)}")

if divs_with_tables:
    print("\nFirst problematic div:")
    print(str(divs_with_tables[0])[:500])
