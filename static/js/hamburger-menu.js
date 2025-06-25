// Hamburger Menu Functionality
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const sidePanel = document.getElementById('sidePanel');
    const overlay = document.getElementById('overlay');
    const closePanelBtn = document.getElementById('closePanelBtn');

    function openPanel() {
        sidePanel.classList.add('open');
        overlay.classList.add('show');
        hamburgerBtn.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closePanel() {
        sidePanel.classList.remove('open');
        overlay.classList.remove('show');
        hamburgerBtn.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Toggle panel on hamburger button click
    hamburgerBtn.addEventListener('click', function() {
        if (sidePanel.classList.contains('open')) {
            closePanel();
        } else {
            openPanel();
        }
    });

    // Close panel on X button click
    closePanelBtn.addEventListener('click', closePanel);

    // Close panel on overlay click
    overlay.addEventListener('click', closePanel);

    // Close panel on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidePanel.classList.contains('open')) {
            closePanel();
        }
    });

    // Prevent panel from closing when clicking inside it
    sidePanel.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});