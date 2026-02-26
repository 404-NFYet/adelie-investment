import os
import re

base_html_path = '/home/ubuntu/adelie-investment/prototypes/concept-toss-1.html'
with open(base_html_path, 'r') as f:
    base_html = f.read()

# Fix CSS styling for No-Square outline
css_to_add = """
        * { -webkit-tap-highlight-color: transparent; }
        button { -webkit-tap-highlight-color: transparent; outline: none !important; }
        button:focus, button:active { outline: none !important; background: transparent; }
        .penguin-img { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .penguin-btn:active .penguin-img { filter: drop-shadow(0 0 20px rgba(255,118,72,0.8)); transform: scale(0.92); }
"""
base_html = base_html.replace('</style>', css_to_add + '\n    </style>')

vars_data = [
    {
        "id": 1,
        "script": """
            const img = document.getElementById('penguin-img');
            document.getElementById('penguin-btn').addEventListener('click', () => {
                img.style.transform = 'translateY(-25px) scale(1.05)';
                img.style.filter = 'drop-shadow(0 15px 15px rgba(255,118,72,0.6))';
                setTimeout(() => { img.style.transform = ''; img.style.filter = ''; }, 300);
            });
        """,
        "emoji": ""
    },
    {
        "id": 2,
        "script": """
            const img = document.getElementById('penguin-img');
            document.getElementById('penguin-btn').addEventListener('click', () => {
                img.style.transform = 'rotate(-15deg) scale(1.05)';
                setTimeout(() => img.style.transform = 'rotate(15deg) scale(1.05)', 150);
                setTimeout(() => img.style.transform = '', 300);
            });
        """,
        "emoji": '<div class="absolute inset-0 flex items-center justify-center pointer-events-none transform -translate-y-2 translate-x-0.5" style="z-index: 20;"><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Sunglasses.png" class="w-16 h-16 opacity-90 drop-shadow-md" /></div>'
    },
    {
        "id": 3,
        "script": """
            const img = document.getElementById('penguin-img');
            const heart = document.getElementById('heart-icon');
            document.getElementById('penguin-btn').addEventListener('click', () => {
                img.style.transform = 'scale(1.15)';
                heart.style.transform = 'scale(1.4)';
                setTimeout(() => { img.style.transform = ''; heart.style.transform = ''; }, 200);
            });
        """,
        "emoji": '<div class="absolute inset-0 flex items-center justify-center pointer-events-none transform -translate-y-6 translate-x-10" style="z-index: 20;"><img id="heart-icon" src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Smilies/Red%20Heart.png" class="w-12 h-12 animate-pulse transition-transform duration-200 drop-shadow-md" /></div>'
    },
    {
        "id": 4,
        "script": """
            const img = document.getElementById('penguin-img');
            const zzz = document.getElementById('zzz-icon');
            document.getElementById('penguin-btn').addEventListener('click', () => {
                zzz.style.opacity = '0';
                img.style.transform = 'translateY(-20px) rotate(10deg) scale(1.1)';
                img.style.filter = 'drop-shadow(0 0 25px rgba(255,200,0,0.8))';
                setTimeout(() => { img.style.transform = ''; img.style.filter = ''; }, 500);
                setTimeout(() => { zzz.style.opacity = '1'; }, 2000);
            });
        """,
        "emoji": '<div id="zzz-icon" class="absolute inset-0 flex items-center justify-center pointer-events-none transform -translate-y-12 translate-x-10 transition-opacity duration-300" style="z-index: 20;"><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Smilies/Zzz.png" class="w-14 h-14 animate-float drop-shadow-md" /></div>'
    }
]

import re
btn_pattern = re.compile(r'<!-- Penguin Mascot.*?<button id="penguin-btn".*?</button>', re.DOTALL)
script_pattern = re.compile(r'<script>\s*const penguinBtn.*?</script>', re.DOTALL)
old_script_pattern = re.compile(r'<script>\s*document\.getElementById\(\'penguin-btn\'\)\.addEventListener\(.*?</script>', re.DOTALL)

for v in vars_data:
    new_btn = f'''<!-- Penguin Mascot (No Square Bounds) -->
                    <button id="penguin-btn" class="penguin-btn relative z-10 w-48 h-48 flex items-center justify-center cursor-pointer group rounded-full" style="background:transparent; border:none; outline:none; -webkit-tap-highlight-color:transparent;">
                        {v['emoji']}
                        <img id="penguin-img" src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Animals/Penguin.png"
                            alt="Penguin" class="penguin-img w-40 h-40 drop-shadow-2xl object-contain m-auto" />
                    </button>'''
    
    new_script = f'''<script>
                        {v['script']}
                    </script>'''
    
    html = btn_pattern.sub(new_btn, base_html)
    if '<script>\n                        const penguinBtn' in html:
        html = script_pattern.sub(new_script, html)
    else:
        html = old_script_pattern.sub(new_script, html)
        
    with open(f'/home/ubuntu/adelie-investment/prototypes/concept-toss-{v["id"]}.html', 'w') as out:
        out.write(html)
