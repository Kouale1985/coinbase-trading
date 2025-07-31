#!/usr/bin/env python3

import re

def markdown_to_html(markdown_text):
    """Simple markdown to HTML converter for our summary document"""
    
    # Start HTML document
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coinbase Trading Bot - Project Summary</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; border-bottom: 2px solid #e74c3c; padding-bottom: 8px; margin-top: 30px; }
        h3 { color: #2980b9; margin-top: 25px; }
        h4 { color: #8e44ad; }
        pre { 
            background: #f8f9fa; 
            padding: 15px; 
            border-radius: 5px; 
            border-left: 4px solid #3498db;
            overflow-x: auto;
        }
        code { 
            background: #f1f2f6; 
            padding: 2px 4px; 
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        ul, ol { margin-left: 20px; }
        li { margin: 5px 0; }
        .emoji { font-size: 1.2em; }
        .status-box {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
        .architecture-box {
            background: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-family: monospace;
        }
        hr { 
            border: none; 
            height: 2px; 
            background: linear-gradient(to right, #3498db, #e74c3c);
            margin: 30px 0;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .checkmark { color: #27ae60; font-weight: bold; }
        .warning { color: #f39c12; font-weight: bold; }
        .error { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
"""
    
    lines = markdown_text.split('\n')
    in_code_block = False
    code_block_content = []
    
    for line in lines:
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End code block
                html += f"<pre><code>{'<br>'.join(code_block_content)}</code></pre>\n"
                code_block_content = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            continue
            
        if in_code_block:
            code_block_content.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue
            
        # Handle horizontal rules
        if line.strip() == '---':
            html += '<hr>\n'
            continue
            
        # Handle headers
        if line.startswith('# '):
            html += f'<h1>{line[2:]}</h1>\n'
        elif line.startswith('## '):
            html += f'<h2>{line[3:]}</h2>\n'
        elif line.startswith('### '):
            html += f'<h3>{line[4:]}</h3>\n'
        elif line.startswith('#### '):
            html += f'<h4>{line[5:]}</h4>\n'
        
        # Handle lists
        elif line.startswith('- '):
            if not lines[lines.index(line)-1].startswith('- ') if lines.index(line) > 0 else True:
                html += '<ul>\n'
            item = line[2:]
            # Handle checkmarks
            item = item.replace('✅', '<span class="checkmark">✅</span>')
            item = item.replace('[x]', '<span class="checkmark">✅</span>')
            item = item.replace('⚠️', '<span class="warning">⚠️</span>')
            item = item.replace('❌', '<span class="error">❌</span>')
            html += f'<li>{item}</li>\n'
            # Check if next line is not a list item
            next_idx = lines.index(line) + 1
            if next_idx < len(lines) and not lines[next_idx].startswith('- '):
                html += '</ul>\n'
                
        # Handle bold text
        elif '**' in line:
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            html += f'<p>{line}</p>\n'
            
        # Handle regular paragraphs
        elif line.strip():
            # Handle inline code
            line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
            # Handle checkmarks and emojis
            line = line.replace('✅', '<span class="checkmark">✅</span>')
            line = line.replace('⚠️', '<span class="warning">⚠️</span>')
            line = line.replace('❌', '<span class="error">❌</span>')
            line = line.replace('🎯', '<span class="emoji">🎯</span>')
            line = line.replace('🚀', '<span class="emoji">🚀</span>')
            line = line.replace('📊', '<span class="emoji">📊</span>')
            line = line.replace('💰', '<span class="emoji">💰</span>')
            line = line.replace('🔧', '<span class="emoji">🔧</span>')
            line = line.replace('📱', '<span class="emoji">📱</span>')
            line = line.replace('🔐', '<span class="emoji">🔐</span>')
            line = line.replace('🎊', '<span class="emoji">🎊</span>')
            line = line.replace('🏆', '<span class="emoji">🏆</span>')
            html += f'<p>{line}</p>\n'
        else:
            html += '<br>\n'
    
    # Close HTML document
    html += """
</body>
</html>"""
    
    return html

def main():
    # Read the markdown file
    with open('Trading_Bot_Project_Summary.md', 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert to HTML
    html_content = markdown_to_html(markdown_content)
    
    # Write HTML file
    with open('Trading_Bot_Project_Summary.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Successfully converted to HTML!")
    print("📄 File saved as: Trading_Bot_Project_Summary.html")
    print("\n🖨️ To create PDF:")
    print("1. Open the HTML file in your browser")
    print("2. Press Ctrl+P (or Cmd+P on Mac)")
    print("3. Select 'Save as PDF' as destination")
    print("4. Choose appropriate settings and save")

if __name__ == "__main__":
    main()