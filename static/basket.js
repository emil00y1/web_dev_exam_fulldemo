document.addEventListener('DOMContentLoaded', () => {
    const basketButton = document.getElementById('basket-button');
    const basketDropdown = document.getElementById('basket-dropdown');
    let lastUpdate = 0;
    const MIN_UPDATE_DELAY = 150;
   
    // Keep your existing dropdown handlers
    document.addEventListener('click', (e) => {
        if (!basketButton.contains(e.target) && !basketDropdown.contains(e.target)) {
            basketDropdown.classList.add('hidden');
        }
    });

    basketButton.addEventListener('click', () => {
        basketDropdown.classList.toggle('hidden');
    });

    // Modified quantity handlers
    document.addEventListener('click', (e) => {
        const decreaseBtn = e.target.closest('.basket-quantity-decrease');
        if (decreaseBtn && canUpdate()) {
            const itemId = decreaseBtn.dataset.itemId;
            const currentQuantity = parseInt(document.getElementById(`basket_quantity_${itemId}`).textContent);
           
            if (currentQuantity > 1) {
                const form = document.getElementById(`frm_decrease_${itemId}`);
                const button = form.querySelector('button[mix-post]');
                if (button) {
                    // Click first, let server handle the update
                    button.click();
                    lastUpdate = Date.now();
                }
            }
        }
    });

    document.addEventListener('click', (e) => {
        const increaseBtn = e.target.closest('.basket-quantity-increase');
        if (increaseBtn && canUpdate()) {
            const itemId = increaseBtn.dataset.itemId;
            const form = document.getElementById(`frm_increase_${itemId}`);
            const button = form.querySelector('button[mix-post]');
            if (button) {
                // Click first, let server handle the update
                button.click();
                lastUpdate = Date.now();
            }
        }
    });

    function canUpdate() {
        return Date.now() - lastUpdate >= MIN_UPDATE_DELAY;
    }
});