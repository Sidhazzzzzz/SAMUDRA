with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

premium_css = """
/* ========================================================
   MODERN "GOOGLE MATERIAL 3" UI OVERHAUL
   ======================================================== */

/* 1. Chat Form & Input */
#chat-input {
    flex: 1;
    background-color: #202124;
    color: #E8EAED;
    border: 1px solid #3C4043;
    padding: 12px 20px;
    border-radius: 24px;
    font-size: 0.95rem;
    font-family: 'Inter', 'Fira Sans', sans-serif;
    outline: none;
    transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
#chat-input:hover {
    background-color: #28292C;
}
#chat-input:focus {
    background-color: #202124;
    border-color: #8AB4F8;
    box-shadow: 0 0 0 2px rgba(138, 180, 248, 0.2);
}

/* 2. Primary Buttons (Transmit, Export) */
.primary-btn {
    background-color: #8AB4F8; /* Google Blue */
    color: #202124 !important; /* High contrast text */
    border: none;
    padding: 10px 24px;
    border-radius: 24px; /* Material pill shape */
    font-family: 'Inter', 'Fira Sans', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    transition: background-color 0.2s ease, box-shadow 0.2s ease, transform 0.1s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.primary-btn:hover {
    background-color: #A8C7FA;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
}
.primary-btn:active {
    background-color: #8AB4F8;
    transform: translateY(1px);
    box-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.primary-btn:disabled {
    background-color: #3C4043;
    color: #9AA0A6 !important;
    box-shadow: none;
    cursor: not-allowed;
    transform: none;
}

/* 3. Export Button Container */
.export-container {
    padding: 0 20px 15px 20px;
}
#export-btn {
    width: 100%;
}

/* 4. Persona Switcher (Segmented Control) */
.persona-switcher {
    display: flex;
    margin: 10px 20px 20px 20px;
    background-color: #202124;
    border: 1px solid #3C4043;
    border-radius: 24px;
    padding: 4px;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}
.persona-btn {
    flex: 1;
    background: transparent;
    color: #9AA0A6;
    border: none;
    padding: 8px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    font-family: 'Inter', 'Fira Sans', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease;
}
.persona-btn:hover:not(.active) {
    background-color: rgba(255, 255, 255, 0.04);
    color: #E8EAED;
}
.persona-btn.active {
    background-color: #8AB4F8;
    color: #202124;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

/* 5. Toggles and Map Controls Hover */
.toggle-label {
    transition: background-color 0.2s ease, border-radius 0.2s ease;
    padding: 4px 8px;
    margin-left: -8px; /* Offset padding */
}
.toggle-label:hover {
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
}

/* 6. Trace Header Hover */
.trace-header {
    transition: background-color 0.2s ease;
}
.trace-header:hover {
    background-color: #28292C; /* Slightly lighter than panel */
}
"""

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css + premium_css)
