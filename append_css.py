import sys

mobile_css = """

/* Mobile Responsive Design */
@media (max-width: 768px) {
    .app-container {
        flex-direction: column;
    }
    
    .sidebar {
        width: 100%;
        height: 65px;
        flex-direction: row;
        border-right: none;
        border-top: 1px solid var(--border);
        order: 2;
        overflow-x: auto;
        padding: 0 10px;
        align-items: center;
        background-color: var(--bg-sidebar);
        position: fixed;
        bottom: 0;
        left: 0;
        z-index: 999;
        -ms-overflow-style: none;  /* IE and Edge */
        scrollbar-width: none;  /* Firefox */
    }
    .sidebar::-webkit-scrollbar {
        display: none;
    }
    
    .logo {
        display: none;
    }
    
    .nav-menu {
        display: flex;
        flex-direction: row;
        width: 100%;
        gap: 5px;
        padding: 0;
        margin: 0;
        height: 100%;
        align-items: center;
    }
    
    .nav-item {
        padding: 8px 12px;
        white-space: nowrap;
        font-size: 0.85rem;
        border-radius: 20px;
        margin: auto 0;
    }
    
    .nav-item svg {
        display: none; /* Hide icons to save space */
    }

    .main-content {
        order: 1;
        width: 100%;
        height: 100%;
        padding-bottom: 70px; /* Space for the bottom navbar */
        overflow-y: auto;
    }

    .top-header {
        padding: 0 16px;
    }

    .grid-layout {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .scrollable-content {
        padding: 16px;
    }

    .status-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }

    .btn {
        width: 100%;
        text-align: center;
        justify-content: center;
    }
}
"""

with open('templates/index.css', 'a', encoding='utf-8') as f:
    f.write(mobile_css)
